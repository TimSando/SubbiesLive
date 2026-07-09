"""Data ingestion orchestration — the main ingestion loop.

Coordinates fetching metadata, competitions, rounds, and games from
FuseSport, and delegates writing/updating events and player stats to
their respective modules.
"""

import logging
from datetime import datetime
from src.core.config import get_settings

from src.ingestion.fusesport import get_teams, get_comp_info, get_game_info
from src.ingestion.transformers import transform_game
from src.ingestion.upserts import (
    upsert_competition,
    upsert_round,
    upsert_team,
    upsert_game,
)
from src.ingestion.game_stats import (
    ingest_game_events,
    ingest_player_history_for_game,
)

import threading

logger = logging.getLogger("ingestion")

_ingestion_lock = threading.Lock()
_is_ingestion_running = False


def is_ingestion_running() -> bool:
    """Check if the ingestion process is currently running."""
    return _is_ingestion_running


def run_ingestion(session_factory):
    """Run a full data ingestion cycle."""
    global _is_ingestion_running

    # Acquire the lock to prevent concurrent executions
    acquired = _ingestion_lock.acquire(blocking=False)
    if not acquired:
        logger.warning("Ingestion process is already running. Skipping this trigger.")
        return

    _is_ingestion_running = True
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Starting data ingestion at {start_time.isoformat()}")
    logger.info("=" * 60)

    session = session_factory()
    settings = get_settings()
    year = settings.current_season_year

    try:
        competitions, raw_teams = get_teams()
        logger.info(f"Processing {len(competitions)} competitions...")

        team_id_map = {}

        for comp_data in competitions:
            comp_id = upsert_competition(
                session, comp_data["id"], comp_data["name"], year=year
            )
            logger.info(f"Processing: {comp_data['name']} (ext_id={comp_data['id']})")

            try:
                comp_info = get_comp_info(comp_data["id"])
            except Exception as e:
                logger.warning(f"  Failed to fetch competition {comp_data['id']}: {e}")
                continue

            for raw_round in comp_info.get("round_objects", []):
                try:
                    round_id = upsert_round(
                        session, comp_id, raw_round["id"], raw_round["name"]
                    )

                    for raw_game in raw_round.get("games", []):
                        try:
                            game_data = transform_game(raw_game, raw_round["id"])

                            ht = game_data["home_team"]
                            at = game_data["away_team"]
                            home_team_id = upsert_team(
                                session,
                                ht["external_id"],
                                ht["name"],
                                ht["club_name"],
                                comp_id,
                                ht["logo_url"],
                            )
                            away_team_id = upsert_team(
                                session,
                                at["external_id"],
                                at["name"],
                                at["club_name"],
                                comp_id,
                                at["logo_url"],
                            )

                            if home_team_id is None or away_team_id is None:
                                logger.debug(
                                    f"    Skipping game {game_data['external_id']} due to missing team info"
                                )
                                continue

                            team_id_map[ht["external_id"]] = home_team_id
                            team_id_map[at["external_id"]] = away_team_id

                            game_id = upsert_game(
                                session, round_id, game_data, home_team_id, away_team_id
                            )

                            # Ingest stats for completed and in-progress games.
                            # For completed games already fully ingested, both helpers
                            # will short-circuit via a DB check before making any HTTP call.
                            # For in-progress games, fetch game_info once and share it.
                            if game_data["status"] in ["completed", "in_progress"]:
                                shared_game_info = None
                                if game_data["status"] == "in_progress":
                                    try:
                                        shared_game_info = get_game_info(
                                            game_data["external_id"]
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"    Failed to fetch in-progress game {game_data['external_id']}: {e}"
                                        )
                                ingest_game_events(
                                    session,
                                    game_id,
                                    game_data["external_id"],
                                    team_id_map,
                                    shared_game_info,
                                )
                                ingest_player_history_for_game(
                                    session,
                                    game_id,
                                    game_data["external_id"],
                                    team_id_map,
                                    shared_game_info,
                                )
                        except Exception as e:
                            logger.error(
                                f"    Failed to process game {raw_game.get('id')}: {e}"
                            )
                            session.rollback()
                            continue
                except Exception as e:
                    logger.error(
                        f"  Failed to process round {raw_round.get('id')}: {e}"
                    )
                    session.rollback()
                    continue

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Ingestion complete in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()
        _is_ingestion_running = False
        _ingestion_lock.release()
