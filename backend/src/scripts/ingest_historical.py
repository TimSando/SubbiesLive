"""Historical Data Ingestion Script.

Reads competition_ids.json and fetches data year-by-year from FuseSport,
writing it to the database via standard ingestion functions.
"""

import json
import argparse
import time
import logging
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from src.ingestion.fusesport import get_comp_info, get_game_info
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
from src.ingestion.engine import get_sync_engine
from src.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ingest_historical")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest historical rugby competition data."
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Specific year to ingest (e.g. 2024). If omitted, all historical years.",
    )
    parser.add_argument(
        "--competition-id",
        type=int,
        help="Specific competition ID to ingest. If specified, only this competition will be processed.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between FuseSport API calls.",
    )
    parser.add_argument(
        "--skip-events",
        action="store_true",
        help="Skip game event and player history ingestion.",
    )
    parser.add_argument(
        "--competition-type",
        choices=["subbies", "premiership"],
        default="subbies",
        help="Competition type to ingest (subbies or premiership).",
    )
    args = parser.parse_args()

    # Load competition ids
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = (
        "competition_ids.json"
        if args.competition_type == "subbies"
        else "premiership_competition_ids.json"
    )
    json_path = os.path.join(script_dir, filename)
    if not os.path.exists(json_path):
        logger.error(f"{filename} not found at {json_path}")
        return

    with open(json_path, "r") as f:
        comp_ids_data = json.load(f)

    # Determine years to process
    settings = get_settings()
    current_year = settings.current_season_year

    if args.year:
        years_to_process = [str(args.year)]
        if str(args.year) not in comp_ids_data:
            logger.error(f"Year {args.year} not found in {filename}")
            return
    else:
        # Process all historical years (all years in JSON except current_year)
        years_to_process = sorted(
            [y for y in comp_ids_data.keys() if int(y) != current_year],
            reverse=True,
        )

    logger.info(f"Starting historical ingestion for years: {years_to_process}")

    # Set up DB connection
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    total_comps = 0
    total_rounds = 0
    total_games = 0

    try:
        for year_str in years_to_process:
            year = int(year_str)
            year_data = comp_ids_data[year_str]
            logger.info(f"--- Processing Year: {year} ---")

            for division_name, division_data in year_data.items():
                season_id = division_data.get("season_id")
                competitions = division_data.get("competitions", [])
                logger.info(
                    f"Processing division '{division_name}' with season_id {season_id} ({len(competitions)} competitions)"
                )

                for comp_entry in competitions:
                    comp_name = comp_entry["competition_name"]
                    comp_ext_id = comp_entry["competition_id"]

                    if args.competition_id and comp_ext_id != args.competition_id:
                        continue

                    logger.info(
                        f"Processing competition: {comp_name} (ext_id={comp_ext_id})"
                    )

                    try:
                        # 1. Upsert Competition
                        comp_id = upsert_competition(
                            session,
                            external_id=comp_ext_id,
                            name=comp_name,
                            year=year,
                            season_id=season_id,
                        )
                        total_comps += 1

                        # 2. Fetch competition info from FuseSport
                        time.sleep(args.delay)
                        comp_info = get_comp_info(comp_ext_id)

                        round_objects = comp_info.get("round_objects", [])
                        logger.info(f"  Found {len(round_objects)} rounds")

                        for raw_round in round_objects:
                            try:
                                raw_round_id = raw_round["id"]
                                raw_round_name = raw_round["name"]
                                raw_games = raw_round.get("games", [])

                                # Check if round exists in DB
                                round_res = session.execute(
                                    text(
                                        "SELECT id FROM rounds WHERE external_id = :eid"
                                    ),
                                    {"eid": raw_round_id},
                                )
                                round_row = round_res.fetchone()

                                round_id = None
                                round_is_fully_ingested = False
                                db_games = {}

                                if round_row:
                                    round_id = round_row[0]
                                    # Fetch existing games for this round
                                    games_res = session.execute(
                                        text(
                                            "SELECT id, external_id, status FROM games WHERE round_id = :rid"
                                        ),
                                        {"rid": round_id},
                                    )
                                    db_games = {
                                        row[1]: (row[0], row[2])
                                        for row in games_res.fetchall()
                                    }

                                    # Verify if all raw games are already fully ingested in DB
                                    all_games_fully_ingested = True
                                    for raw_game in raw_games:
                                        game_data = transform_game(
                                            raw_game, raw_round_id
                                        )
                                        game_ext_id = game_data["external_id"]
                                        game_status = game_data["status"]

                                        if game_ext_id not in db_games:
                                            all_games_fully_ingested = False
                                            break

                                        db_game_id, stored_status = db_games[
                                            game_ext_id
                                        ]
                                        if stored_status != game_status:
                                            all_games_fully_ingested = False
                                            break

                                        if (
                                            game_status == "completed"
                                            and not args.skip_events
                                        ):
                                            # Check game events
                                            events_exist = session.execute(
                                                text(
                                                    "SELECT EXISTS(SELECT 1 FROM game_events WHERE game_id = :gid)"
                                                ),
                                                {"gid": db_game_id},
                                            ).scalar()
                                            if not events_exist:
                                                all_games_fully_ingested = False
                                                break

                                            # Check player history
                                            existing_sheets = session.execute(
                                                text(
                                                    "SELECT COUNT(DISTINCT team_id) FROM player_history WHERE game_id = :gid"
                                                ),
                                                {"gid": db_game_id},
                                            ).scalar()
                                            if existing_sheets < 2:
                                                all_games_fully_ingested = False
                                                break

                                    if all_games_fully_ingested and len(raw_games) > 0:
                                        round_is_fully_ingested = True

                                if round_is_fully_ingested:
                                    logger.info(
                                        f"  Round '{raw_round_name}' (ext_id={raw_round_id}) already fully ingested. Skipping all games."
                                    )
                                    total_rounds += 1
                                    total_games += len(raw_games)
                                    continue

                                # 3. Upsert Round
                                if round_id is None:
                                    round_id = upsert_round(
                                        session,
                                        competition_id=comp_id,
                                        external_id=raw_round_id,
                                        name=raw_round_name,
                                    )
                                total_rounds += 1

                                for raw_game in raw_games:
                                    try:
                                        game_data = transform_game(
                                            raw_game, raw_round_id
                                        )
                                        game_ext_id = game_data["external_id"]
                                        game_status = game_data["status"]

                                        # Check if individual game is already fully ingested
                                        is_game_ingested = False
                                        db_game_id = None
                                        if round_row and game_ext_id in db_games:
                                            db_game_id, stored_status = db_games[
                                                game_ext_id
                                            ]
                                            if stored_status == game_status:
                                                if (
                                                    game_status != "completed"
                                                    or args.skip_events
                                                ):
                                                    is_game_ingested = True
                                                else:
                                                    events_exist = session.execute(
                                                        text(
                                                            "SELECT EXISTS(SELECT 1 FROM game_events WHERE game_id = :gid)"
                                                        ),
                                                        {"gid": db_game_id},
                                                    ).scalar()
                                                    existing_sheets = session.execute(
                                                        text(
                                                            "SELECT COUNT(DISTINCT team_id) FROM player_history WHERE game_id = :gid"
                                                        ),
                                                        {"gid": db_game_id},
                                                    ).scalar()
                                                    if (
                                                        events_exist
                                                        and existing_sheets >= 2
                                                    ):
                                                        is_game_ingested = True

                                        if is_game_ingested:
                                            logger.info(
                                                f"    Game {game_ext_id} already fully ingested. Skipping."
                                            )
                                            total_games += 1
                                            continue

                                        ht = game_data["home_team"]
                                        at = game_data["away_team"]

                                        # 4. Upsert Teams
                                        home_team_id = upsert_team(
                                            session,
                                            external_id=ht["external_id"],
                                            name=ht["name"],
                                            club_name=ht["club_name"],
                                            competition_id=comp_id,
                                            logo_url=ht.get("logo_url"),
                                        )
                                        away_team_id = upsert_team(
                                            session,
                                            external_id=at["external_id"],
                                            name=at["name"],
                                            club_name=at["club_name"],
                                            competition_id=comp_id,
                                            logo_url=at.get("logo_url"),
                                        )

                                        if home_team_id is None or away_team_id is None:
                                            logger.warning(
                                                f"    Skipping game {game_data['external_id']} due to missing team info"
                                            )
                                            continue

                                        # Create team ID map for stats ingestion
                                        team_id_map = {
                                            ht["external_id"]: home_team_id,
                                            at["external_id"]: away_team_id,
                                        }

                                        # 5. Upsert Game
                                        game_id = upsert_game(
                                            session,
                                            round_id=round_id,
                                            game_data=game_data,
                                            home_team_id=home_team_id,
                                            away_team_id=away_team_id,
                                        )
                                        total_games += 1

                                        # 6. Ingest events and player history if completed
                                        if (
                                            game_data["status"] == "completed"
                                            and not args.skip_events
                                        ):
                                            time.sleep(args.delay)
                                            try:
                                                ingest_game_events(
                                                    session,
                                                    game_id=game_id,
                                                    game_external_id=game_data[
                                                        "external_id"
                                                    ],
                                                    team_id_map=team_id_map,
                                                    game_info=None,
                                                )
                                            except Exception as event_err:
                                                logger.warning(
                                                    f"      Failed to ingest game events for game {game_data['external_id']}: {event_err}"
                                                )

                                            try:
                                                ingest_player_history_for_game(
                                                    session,
                                                    game_id=game_id,
                                                    game_external_id=game_data[
                                                        "external_id"
                                                    ],
                                                    team_id_map=team_id_map,
                                                    game_info=None,
                                                )
                                            except Exception as player_err:
                                                logger.warning(
                                                    f"      Failed to ingest player history for game {game_data['external_id']}: {player_err}"
                                                )

                                    except Exception as game_err:
                                        logger.error(
                                            f"    Error processing game {raw_game.get('id')}: {game_err}"
                                        )
                                        session.rollback()
                                        continue

                            except Exception as round_err:
                                logger.error(
                                    f"  Error processing round {raw_round.get('id')}: {round_err}"
                                )
                                session.rollback()
                                continue

                    except Exception as comp_err:
                        logger.error(
                            f"Error processing competition {comp_name} ({comp_ext_id}): {comp_err}"
                        )
                        session.rollback()
                        continue

        logger.info("Historical Ingestion Completed successfully!")
        logger.info(f"Total Competitions processed: {total_comps}")
        logger.info(f"Total Rounds processed: {total_rounds}")
        logger.info(f"Total Games processed: {total_games}")

    except Exception as e:
        logger.error(f"Fatal error in ingestion process: {e}", exc_info=True)
    finally:
        session.close()


if __name__ == "__main__":
    main()
