"""Data ingestion service — runs as a background task inside the FastAPI process.

Fetches data from FuseSport and populates PostgreSQL.
Runs an initial sync on startup, then schedules periodic updates via APScheduler.

Schedule:
  - Sunday to Friday: once daily at 6:00 AM AEST
  - Saturday (game day): every 30 minutes from 9:00 AM to 6:00 PM AEST
"""

import os
import logging
import threading
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.ingestion.fusesport import get_teams, get_comp_info, get_game_info
from src.ingestion.transformers import (
    extract_club_name,
    extract_round_number,
    transform_game,
    transform_game_event,
)

logger = logging.getLogger("ingestion")

TIMEZONE = os.environ.get("TZ", "Australia/Sydney")

# Module-level scheduler reference so we can shut it down cleanly
_scheduler: BackgroundScheduler | None = None


def _get_sync_engine():
    """Create a synchronous SQLAlchemy engine for ingestion.

    The ingestion worker uses sync psycopg2 (not asyncpg) because it runs
    in a background thread separate from the async FastAPI event loop.
    """
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    )
    # If the URL still has asyncpg or is empty, build from components
    if not db_url or "+asyncpg" in db_url:
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_USER', 'subbiesstats')}"
            f":{os.environ.get('POSTGRES_PASSWORD', 'subbiesstats_dev_2026')}"
            f"@{os.environ.get('POSTGRES_HOST', 'db')}"
            f":5432/{os.environ.get('POSTGRES_DB', 'subbiesstats')}"
        )
    return create_engine(db_url, echo=False, pool_pre_ping=True)


# ---------------------------------------------------------------------------
# Upsert helpers (raw SQL for simplicity and performance)
# ---------------------------------------------------------------------------

def upsert_club(session, club_name: str, logo_url: str = None) -> int | None:
    if not club_name:
        return None
    result = session.execute(
        text("SELECT id FROM clubs WHERE name = :name"), {"name": club_name}
    )
    row = result.fetchone()
    if row:
        return row[0]

    result = session.execute(
        text("INSERT INTO clubs (name, short_name, logo_url) VALUES (:name, :short_name, :logo_url) RETURNING id"),
        {"name": club_name, "short_name": club_name, "logo_url": logo_url}
    )
    session.commit()
    return result.fetchone()[0]


def upsert_competition(session, external_id: int, name: str) -> int:
    result = session.execute(
        text("SELECT id FROM competitions WHERE external_id = :eid"), {"eid": external_id}
    )
    row = result.fetchone()
    if row:
        return row[0]

    result = session.execute(
        text("INSERT INTO competitions (name, external_id) VALUES (:name, :eid) RETURNING id"),
        {"name": name, "eid": external_id}
    )
    session.commit()
    return result.fetchone()[0]


def upsert_round(session, competition_id: int, external_id: int, name: str) -> int:
    result = session.execute(
        text("SELECT id FROM rounds WHERE external_id = :eid"), {"eid": external_id}
    )
    row = result.fetchone()
    if row:
        return row[0]

    number = extract_round_number(name)
    result = session.execute(
        text("""INSERT INTO rounds (competition_id, name, number, external_id) 
                VALUES (:cid, :name, :number, :eid) RETURNING id"""),
        {"cid": competition_id, "name": name, "number": number, "eid": external_id}
    )
    session.commit()
    return result.fetchone()[0]


def upsert_team(session, external_id: int, name: str, club_name: str,
                competition_id: int, logo_url: str = None) -> int:
    result = session.execute(
        text("SELECT id FROM teams WHERE external_id = :eid"), {"eid": external_id}
    )
    row = result.fetchone()
    if row:
        return row[0]

    club_id = upsert_club(session, club_name, logo_url)
    if not club_id:
        return None
    result = session.execute(
        text("""INSERT INTO teams (club_id, competition_id, name, external_id) 
                VALUES (:club_id, :comp_id, :name, :eid) RETURNING id"""),
        {"club_id": club_id, "comp_id": competition_id, "name": name, "eid": external_id}
    )
    session.commit()
    return result.fetchone()[0]


def upsert_game(session, round_id: int, game_data: dict, home_team_id: int, away_team_id: int) -> int:
    result = session.execute(
        text("SELECT id, home_score FROM games WHERE external_id = :eid"),
        {"eid": game_data["external_id"]}
    )
    row = result.fetchone()

    if row:
        if game_data["home_score"] is not None and row[1] is None:
            session.execute(
                text("""UPDATE games SET home_score = :hs, away_score = :as_, status = :status 
                        WHERE id = :id"""),
                {"hs": game_data["home_score"], "as_": game_data["away_score"],
                 "status": game_data["status"], "id": row[0]}
            )
            session.commit()
            logger.info(f"Updated game {game_data['external_id']} with scores")
        return row[0]

    result = session.execute(
        text("""INSERT INTO games (round_id, home_team_id, away_team_id, game_date, 
                location, home_score, away_score, status, external_id) 
                VALUES (:rid, :htid, :atid, :gd, :loc, :hs, :as_, :status, :eid) 
                RETURNING id"""),
        {
            "rid": round_id, "htid": home_team_id, "atid": away_team_id,
            "gd": game_data["game_date"], "loc": game_data["location"],
            "hs": game_data["home_score"], "as_": game_data["away_score"],
            "status": game_data["status"], "eid": game_data["external_id"],
        }
    )
    session.commit()
    return result.fetchone()[0]


def upsert_player(session, player_data: dict) -> int | None:
    if not player_data:
        return None

    result = session.execute(
        text("SELECT id FROM players WHERE external_id = :eid"),
        {"eid": player_data["external_id"]}
    )
    row = result.fetchone()
    if row:
        return row[0]

    dob = None
    if player_data.get("dob"):
        try:
            from dateutil import parser as dateparser
            dob = dateparser.parse(player_data["dob"]).date()
        except (ValueError, TypeError):
            pass

    result = session.execute(
        text("""INSERT INTO players (name, dob, image_url, thumbnail_url, external_id) 
                VALUES (:name, :dob, :img, :thumb, :eid) RETURNING id"""),
        {
            "name": player_data["name"], "dob": dob,
            "img": player_data.get("image_url"), "thumb": player_data.get("thumbnail_url"),
            "eid": player_data["external_id"],
        }
    )
    session.commit()
    return result.fetchone()[0]


def ingest_game_events(session, game_id: int, game_external_id: int, team_id_map: dict):
    """Fetch and ingest game events for a completed game."""
    result = session.execute(
        text("SELECT COUNT(*) FROM game_events WHERE game_id = :gid"), {"gid": game_id}
    )
    if result.scalar() > 0:
        return

    try:
        game_info = get_game_info(game_external_id)
    except Exception as e:
        logger.warning(f"Failed to fetch game {game_external_id} details: {e}")
        return

    events_ingested = 0
    for score_sheet_key in ["home_score_sheet", "away_score_sheet"]:
        score_sheet = game_info.get(score_sheet_key, {})
        if not score_sheet:
            continue

        sheet_team_ext_id = score_sheet.get("team_id")

        for raw_event in score_sheet.get("game_events", []):
            if raw_event.get("team_id") != sheet_team_ext_id:
                continue

            event_data = transform_game_event(raw_event, game_external_id)

            team_ext_id = event_data["team_external_id"]
            db_team_id = team_id_map.get(team_ext_id)
            if not db_team_id:
                continue

            player_id = upsert_player(session, event_data.get("player"))

            result = session.execute(
                text("SELECT id FROM game_events WHERE external_id = :eid"),
                {"eid": str(event_data["external_id"])}
            )
            if result.fetchone():
                continue

            session.execute(
                text("""INSERT INTO game_events (game_id, team_id, player_id, event_type, 
                        player_number, points, text, external_created_at, external_id) 
                        VALUES (:gid, :tid, :pid, :et, :pn, :pts, :txt, :eca, :eid)"""),
                {
                    "gid": game_id, "tid": db_team_id, "pid": player_id,
                    "et": event_data["event_type"], "pn": event_data["player_number"],
                    "pts": event_data["points"], "txt": event_data["text"],
                    "eca": event_data["external_created_at"],
                    "eid": str(event_data["external_id"]),
                }
            )
            events_ingested += 1

    session.commit()
    if events_ingested > 0:
        logger.info(f"  Ingested {events_ingested} events for game {game_external_id}")


# ---------------------------------------------------------------------------
# Main ingestion cycle
# ---------------------------------------------------------------------------

def run_ingestion(session_factory):
    """Run a full data ingestion cycle."""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Starting data ingestion at {start_time.isoformat()}")
    logger.info("=" * 60)

    session = session_factory()

    try:
        competitions, raw_teams = get_teams()
        logger.info(f"Processing {len(competitions)} competitions...")

        team_id_map = {}

        for comp_data in competitions:
            comp_id = upsert_competition(session, comp_data["id"], comp_data["name"])
            logger.info(f"Processing: {comp_data['name']} (ext_id={comp_data['id']})")

            try:
                comp_info = get_comp_info(comp_data["id"])
            except Exception as e:
                logger.warning(f"  Failed to fetch competition {comp_data['id']}: {e}")
                continue

            for raw_round in comp_info.get("round_objects", []):
                try:
                    round_id = upsert_round(session, comp_id, raw_round["id"], raw_round["name"])

                    for raw_game in raw_round.get("games", []):
                        try:
                            game_data = transform_game(raw_game, raw_round["id"])

                            ht = game_data["home_team"]
                            at = game_data["away_team"]
                            home_team_id = upsert_team(
                                session, ht["external_id"], ht["name"],
                                ht["club_name"], comp_id, ht["logo_url"]
                            )
                            away_team_id = upsert_team(
                                session, at["external_id"], at["name"],
                                at["club_name"], comp_id, at["logo_url"]
                            )

                            team_id_map[ht["external_id"]] = home_team_id
                            team_id_map[at["external_id"]] = away_team_id

                            game_id = upsert_game(session, round_id, game_data, home_team_id, away_team_id)

                            if game_data["status"] == "completed":
                                ingest_game_events(session, game_id, game_data["external_id"], team_id_map)
                        except Exception as e:
                            logger.error(f"    Failed to process game {raw_game.get('id')}: {e}")
                            session.rollback()
                            continue
                except Exception as e:
                    logger.error(f"  Failed to process round {raw_round.get('id')}: {e}")
                    session.rollback()
                    continue

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Ingestion complete in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Lifecycle hooks — called from FastAPI lifespan
# ---------------------------------------------------------------------------

def start_ingestion_scheduler():
    """Start the ingestion scheduler as a background thread.

    Called from FastAPI's lifespan startup hook.
    """
    global _scheduler

    engine = _get_sync_engine()
    Session = sessionmaker(bind=engine)

    # Run initial ingestion in a background thread so it doesn't block startup
    def _initial_run():
        logger.info("Running initial data ingestion...")
        run_ingestion(Session)

    init_thread = threading.Thread(target=_initial_run, daemon=True)
    init_thread.start()

    # Set up scheduled jobs
    _scheduler = BackgroundScheduler(timezone=TIMEZONE)

    # Daily sync at 6:00 AM on Sun-Fri
    _scheduler.add_job(
        run_ingestion,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu,fri", hour=6, minute=0, timezone=TIMEZONE),
        args=[Session],
        id="daily_ingestion",
        name="Daily ingestion (Sun-Fri 6:00 AM)",
    )

    # Game day sync every 30 min on Saturday, 9 AM - 6 PM
    _scheduler.add_job(
        run_ingestion,
        CronTrigger(day_of_week="sat", hour="9-17", minute="0,30", timezone=TIMEZONE),
        args=[Session],
        id="gameday_ingestion",
        name="Game day ingestion (Sat every 30 min, 9 AM - 6 PM)",
    )

    _scheduler.start()

    logger.info("Ingestion scheduler started:")
    logger.info("  • Sun-Fri: Daily at 6:00 AM AEST")
    logger.info("  • Saturday: Every 30 min, 9:00 AM - 6:00 PM AEST")


def stop_ingestion_scheduler():
    """Shut down the ingestion scheduler cleanly.

    Called from FastAPI's lifespan shutdown hook.
    """
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped.")
        _scheduler = None
