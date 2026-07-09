"""Monitoring script for historical ingestion progress."""

import json
import os
import argparse
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.ingestion.engine import get_sync_engine
from src.core.config import get_settings


def main():
    parser = argparse.ArgumentParser(
        description="Monitor historical ingestion progress."
    )
    parser.add_argument(
        "--competition-type",
        choices=["subbies", "premiership"],
        default="subbies",
        help="Competition type to monitor (subbies or premiership).",
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
        print(f"{filename} not found at {json_path}")
        return

    with open(json_path, "r") as f:
        comp_ids_data = json.load(f)

    settings = get_settings()
    current_year = settings.current_season_year

    # Set up DB connection
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all years except current_year
        years = sorted(
            [y for y in comp_ids_data.keys() if int(y) != current_year],
            reverse=True,
        )

        print("\n=== HISTORICAL INGESTION MONITOR ===")
        print(f"Current Season Year: {current_year} (Skipped)\n")

        for year_str in years:
            year = int(year_str)
            # Find all expected comp ids for this year
            expected_comps = []
            year_data = comp_ids_data[year_str]
            for division_name, division_data in year_data.items():
                for comp_entry in division_data.get("competitions", []):
                    expected_comps.append(
                        {
                            "name": comp_entry["competition_name"],
                            "id": comp_entry["competition_id"],
                        }
                    )

            total_expected = len(expected_comps)
            if total_expected == 0:
                continue

            # Query DB for competitions present in this year
            db_comps = session.execute(
                text("SELECT name, external_id FROM competitions WHERE year = :year"),
                {"year": year},
            ).fetchall()

            db_comp_map = {row[1]: row[0] for row in db_comps}

            # For each expected competition, check status and game count
            comp_details = []
            loaded_count = 0
            for comp in expected_comps:
                comp_id = comp["id"]
                comp_name = comp["name"]
                if comp_id in db_comp_map:
                    loaded_count += 1
                    # Query game count
                    game_count = session.execute(
                        text(
                            """
                            SELECT COUNT(g.id) 
                            FROM games g 
                            JOIN rounds r ON g.round_id = r.id 
                            JOIN competitions c ON r.competition_id = c.id 
                            WHERE c.external_id = :comp_id
                        """
                        ),
                        {"comp_id": comp_id},
                    ).scalar()
                    comp_details.append(
                        f"    - {comp_name}: {game_count} games (Loaded)"
                    )
                else:
                    comp_details.append(f"    - {comp_name}: Pending")

            percent = (loaded_count / total_expected) * 100

            # Print progress bar
            bar_length = 20
            filled_length = int(round(bar_length * loaded_count / total_expected))
            bar = "=" * filled_length + "-" * (bar_length - filled_length)

            print(
                f"Year {year}: [{bar}] {loaded_count}/{total_expected} Competitions ({percent:.1f}%)"
            )
            for detail in comp_details:
                print(detail)
            print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
