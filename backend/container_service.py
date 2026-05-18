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

from src.ingestion.fusesport import get_teams, get_comp_info, get_game_info, get_score_sheet
from src.ingestion.transformers import (
    extract_club_name,
    extract_round_number,
    transform_game,
    transform_game_event,
)
from src.scripts.seed_mapping import seed_mapping

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

def upsert_club(session, club_name: str, logo_url: str = None, competition_id: int = None) -> int | None:
    if not club_name:
        return None
        
    result = session.execute(
        text("SELECT id, competition_mapping_id FROM clubs WHERE name = :name"), {"name": club_name}
    )
    row = result.fetchone()
    
    mapping_id = None
    if competition_id:
        comp_res = session.execute(
            text("SELECT competition_mapping_id FROM competitions WHERE id = :cid"),
            {"cid": competition_id}
        )
        mapping_id = comp_res.scalar()

    if row:
        club_id = row[0]
        if mapping_id and not row[1]:
            session.execute(
                text("UPDATE clubs SET competition_mapping_id = :mid WHERE id = :id"),
                {"mid": mapping_id, "id": club_id}
            )
            session.commit()
        return club_id

    result = session.execute(
        text("INSERT INTO clubs (name, short_name, logo_url, competition_mapping_id) VALUES (:name, :short_name, :logo_url, :mid) RETURNING id"),
        {"name": club_name, "short_name": club_name, "logo_url": logo_url, "mid": mapping_id}
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

    # Try to find a mapping
    mapping_res = session.execute(
        text("SELECT id FROM competition_mapping WHERE name = :name"), {"name": name}
    )
    mapping_row = mapping_res.fetchone()
    mapping_id = mapping_row[0] if mapping_row else None

    result = session.execute(
        text("INSERT INTO competitions (name, external_id, competition_mapping_id) VALUES (:name, :eid, :mid) RETURNING id"),
        {"name": name, "eid": external_id, "mid": mapping_id}
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

    club_id = upsert_club(session, club_name, logo_url, competition_id)
    if not club_id:
        logger.debug(f"Skipping team {name} ({external_id}) as no valid club could be determined")
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
    # We don't skip if events exist anymore, as we want to handle partial updates or missing data.
    # The inner loop handles existing records via external_id check.

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


def ingest_player_history(session, game_id: int, score_sheet_id: str, team_id_map: dict):
    """Fetch a score sheet and upsert player_history records.
    
    Args:
        session:        SQLAlchemy session
        game_id:        Internal DB game ID
        score_sheet_id: FuseSport UUID for the score sheet
        team_id_map:    Dict mapping external team IDs -> internal team DB IDs
    """
    # Skip if already ingested for this game (check both teams)
    existing = session.execute(
        text("SELECT COUNT(*) FROM player_history WHERE game_id = :gid"),
        {"gid": game_id}
    ).scalar()
    if existing > 0:
        return  # Already processed

    try:
        records = get_score_sheet(score_sheet_id)
    except Exception as e:
        logger.warning(f"Failed to fetch score sheet {score_sheet_id}: {e}")
        return

    inserted = 0
    for record in records:
        member = record.get("member")
        if not member:
            continue  # Skip empty roster slots

        # Resolve player (upsert via existing helper)
        player_data = {
            "external_id": member["id"],
            "name": member["name"],
            "dob": member.get("dob"),
            "image_url": member.get("image"),
            "thumbnail_url": member.get("thumbnail"),
        }
        player_id = upsert_player(session, player_data)
        if not player_id:
            continue

        # Resolve internal team ID
        team_ext_id = record.get("team_id")
        db_team_id = team_id_map.get(team_ext_id)
        if not db_team_id:
            logger.debug(f"  Skipping player {member['name']}: unknown team ext_id {team_ext_id}")
            continue

        # Upsert the player_history record
        session.execute(
            text("""
                INSERT INTO player_history (
                    player_id, game_id, team_id, position_id, player_number, points,
                    tries, conversions, penalty_goals, drop_goals,
                    yellow_cards, red_cards, blue_cards,
                    medal_points_1, medal_points_2, medal_points_3,
                    coach_points_1, coach_points_2, coach_points_3,
                    card_text
                ) VALUES (
                    :pid, :gid, :tid, :pos, :pnum, :pts,
                    :tries, :conv, :pen, :dg,
                    :yc, :rc, :bc,
                    :m1, :m2, :m3,
                    :c1, :c2, :c3,
                    :ctext
                )
                ON CONFLICT (player_id, game_id, team_id) DO UPDATE SET
                    points        = EXCLUDED.points,
                    tries         = EXCLUDED.tries,
                    conversions   = EXCLUDED.conversions,
                    penalty_goals = EXCLUDED.penalty_goals,
                    drop_goals    = EXCLUDED.drop_goals,
                    yellow_cards  = EXCLUDED.yellow_cards,
                    red_cards     = EXCLUDED.red_cards,
                    blue_cards    = EXCLUDED.blue_cards,
                    medal_points_1 = EXCLUDED.medal_points_1,
                    medal_points_2 = EXCLUDED.medal_points_2,
                    medal_points_3 = EXCLUDED.medal_points_3,
                    coach_points_1 = EXCLUDED.coach_points_1,
                    coach_points_2 = EXCLUDED.coach_points_2,
                    coach_points_3 = EXCLUDED.coach_points_3,
                    card_text     = EXCLUDED.card_text
            """),
            {
                "pid": player_id, "gid": game_id, "tid": db_team_id,
                "pos": record.get("position_id"),
                "pnum": record.get("player_number"),
                "pts": record.get("points", 0),
                "tries": record.get("rugby_union_try", 0),
                "conv":  record.get("rugby_union_conversion", 0),
                "pen":   record.get("rugby_union_penalty_goal", 0),
                "dg":    record.get("rugby_union_drop_goal", 0),
                "yc":    record.get("rugby_union_yellow_card", 0),
                "rc":    record.get("rugby_union_red_card", 0),
                "bc":    record.get("rugby_union_blue_card", 0),
                "m1":    record.get("rugby_union_medal_points_1", 0),
                "m2":    record.get("rugby_union_medal_points_2", 0),
                "m3":    record.get("rugby_union_medal_points_3", 0),
                "c1":    record.get("rugby_union_coach_points_1", 0),
                "c2":    record.get("rugby_union_coach_points_2", 0),
                "c3":    record.get("rugby_union_coach_points_3", 0),
                "ctext": record.get("card_text") or None,
            }
        )
        inserted += 1

    session.commit()
    if inserted > 0:
        logger.info(f"  Ingested {inserted} player_history rows for score sheet {score_sheet_id}")


def ingest_player_history_for_game(session, game_id: int, game_external_id: int, team_id_map: dict):
    """Fetch game details to get score sheet IDs and ingest history."""
    # Guard against already processed games (checked inside ingest_player_history too)
    # We no longer skip games that have history records. 
    # ingest_player_history handles upserts via ON CONFLICT.

    try:
        game_info = get_game_info(game_external_id)
    except Exception as e:
        logger.warning(f"Failed to fetch game {game_external_id} details for history: {e}")
        return

    for sheet_key in ["home_score_sheet", "away_score_sheet"]:
        sheet = game_info.get(sheet_key, {})
        sheet_id = sheet.get("id")
        if sheet_id:
            ingest_player_history(session, game_id, sheet_id, team_id_map)


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

                            if home_team_id is None or away_team_id is None:
                                logger.debug(f"    Skipping game {game_data['external_id']} due to missing team info")
                                continue

                            team_id_map[ht["external_id"]] = home_team_id
                            team_id_map[at["external_id"]] = away_team_id

                            game_id = upsert_game(session, round_id, game_data, home_team_id, away_team_id)

                            # Ingest stats for both completed and in-progress games to ensure up-to-date data
                            if game_data["status"] in ["completed", "in_progress"]:
                                ingest_game_events(session, game_id, game_data["external_id"], team_id_map)
                                ingest_player_history_for_game(session, game_id, game_data["external_id"], team_id_map)
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
        logger.info("Checking for competition mapping seed...")
        try:
            csv_path = os.environ.get("MAPPING_CSV_PATH", "/app/src/scripts/competition_parent_mapping - Sheet1.csv")
            seed_mapping(csv_path)
        except Exception as e:
            logger.error(f"Failed to seed mapping: {e}")

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
