import os
import json
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_club_details")


def get_engine():
    db_url = os.environ.get(
        "DATABASE_URL_SYNC", os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    )
    if not db_url or "+asyncpg" in db_url:
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_USER', 'subbiesstats')}"
            f":{os.environ.get('POSTGRES_PASSWORD', 'subbiesstats_dev_2026')}"
            f"@{os.environ.get('POSTGRES_HOST', 'db')}"
            f":5432/{os.environ.get('POSTGRES_DB', 'subbiesstats')}"
        )
    return create_engine(db_url)


def merge_duplicate_clubs():
    engine = get_engine()
    try:
        with engine.begin() as conn:
            # 1. Fetch IDs of Colleagues and Colleagues Colts
            res = conn.execute(text("SELECT id FROM clubs WHERE name = 'Colleagues'"))
            colleagues_id = res.scalar()

            res = conn.execute(
                text("SELECT id FROM clubs WHERE name = 'Colleagues Colts'")
            )
            colleagues_colts_id = res.scalar()

            # 2. Fetch IDs of Balmain and Balmain Grey Wolves
            res = conn.execute(text("SELECT id FROM clubs WHERE name = 'Balmain'"))
            balmain_id = res.scalar()

            res = conn.execute(
                text("SELECT id FROM clubs WHERE name = 'Balmain Grey Wolves'")
            )
            balmain_wolves_id = res.scalar()

            # Merge Colleagues Colts -> Colleagues
            if colleagues_id and colleagues_colts_id:
                logger.info(
                    f"Merging 'Colleagues Colts' (ID: {colleagues_colts_id}) into 'Colleagues' (ID: {colleagues_id})..."
                )
                # Update teams
                res_teams = conn.execute(
                    text(
                        "UPDATE teams SET club_id = :parent_id WHERE club_id = :duplicate_id"
                    ),
                    {"parent_id": colleagues_id, "duplicate_id": colleagues_colts_id},
                )
                # Delete duplicate club
                conn.execute(
                    text("DELETE FROM clubs WHERE id = :duplicate_id"),
                    {"duplicate_id": colleagues_colts_id},
                )
                logger.info(
                    f"Merged Colleagues Colts. Updated {res_teams.rowcount} teams."
                )

            # Merge Balmain Grey Wolves -> Balmain
            if balmain_id and balmain_wolves_id:
                logger.info(
                    f"Merging 'Balmain Grey Wolves' (ID: {balmain_wolves_id}) into 'Balmain' (ID: {balmain_id})..."
                )
                # Update teams
                res_teams = conn.execute(
                    text(
                        "UPDATE teams SET club_id = :parent_id WHERE club_id = :duplicate_id"
                    ),
                    {"parent_id": balmain_id, "duplicate_id": balmain_wolves_id},
                )
                # Delete duplicate club
                conn.execute(
                    text("DELETE FROM clubs WHERE id = :duplicate_id"),
                    {"duplicate_id": balmain_wolves_id},
                )
                logger.info(
                    f"Merged Balmain Grey Wolves. Updated {res_teams.rowcount} teams."
                )
    except Exception as e:
        logger.error(f"Error merging duplicate clubs: {e}")


def seed_club_details(json_path: str):
    # Run merge of duplicates first to clean up existing databases
    merge_duplicate_clubs()

    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        return

    logger.info(f"Reading scraped club details from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        clubs_data = json.load(f)

    engine = get_engine()
    with engine.begin() as conn:
        count = 0
        for club in clubs_data:
            name = club.get("name")
            if not name:
                continue

            # Update the club record
            res = conn.execute(
                text("""
                    UPDATE clubs 
                    SET about_text = :about,
                        division_info = :div,
                        grades_count = :grades,
                        training_info = :training,
                        has_womens_team = :womens,
                        home_ground_name = :ground,
                        home_ground_map_url = :map_url,
                        website_url = :website,
                        facebook_url = :facebook,
                        instagram_url = :instagram,
                        tiktok_url = :tiktok
                    WHERE name = :name OR short_name = :name
                """),
                {
                    "name": name,
                    "about": club.get("about_text"),
                    "div": club.get("division_info"),
                    "grades": club.get("grades_count"),
                    "training": club.get("training_info"),
                    "womens": club.get("has_womens_team", False),
                    "ground": club.get("home_ground_name"),
                    "map_url": club.get("home_ground_map_url"),
                    "website": club.get("website_url"),
                    "facebook": club.get("facebook_url"),
                    "instagram": club.get("instagram_url"),
                    "tiktok": club.get("tiktok_url"),
                },
            )
            if res.rowcount > 0:
                count += 1
                logger.info(f"Updated club '{name}' successfully.")
            else:
                # If exact name/short_name not found, check with a partial match
                partial_res = conn.execute(
                    text("""
                        UPDATE clubs 
                        SET about_text = :about,
                            division_info = :div,
                            grades_count = :grades,
                            training_info = :training,
                            has_womens_team = :womens,
                            home_ground_name = :ground,
                            home_ground_map_url = :map_url,
                            website_url = :website,
                            facebook_url = :facebook,
                            instagram_url = :instagram,
                            tiktok_url = :tiktok
                        WHERE name ILIKE :partial
                    """),
                    {
                        "partial": f"%{name}%",
                        "about": club.get("about_text"),
                        "div": club.get("division_info"),
                        "grades": club.get("grades_count"),
                        "training": club.get("training_info"),
                        "womens": club.get("has_womens_team", False),
                        "ground": club.get("home_ground_name"),
                        "map_url": club.get("home_ground_map_url"),
                        "website": club.get("website_url"),
                        "facebook": club.get("facebook_url"),
                        "instagram": club.get("instagram_url"),
                        "tiktok": club.get("tiktok_url"),
                    },
                )
                if partial_res.rowcount > 0:
                    count += 1
                    logger.info(f"Updated club '{name}' via partial match.")
                else:
                    logger.warning(f"Club '{name}' not found in database. Skipping.")

        logger.info(f"Successfully updated details for {count} clubs.")


def seed_club_details_if_empty():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Check if there are any clubs that have details populated
            res = conn.execute(
                text("SELECT COUNT(*) FROM clubs WHERE about_text IS NOT NULL")
            )
            count = res.scalar()
            if count == 0:
                logger.info("Club details are empty. Running automatic seed...")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(script_dir, "club_scraped_data.json")
                seed_club_details(json_path)
            else:
                logger.info("Club details already populated. Skipping automatic seed.")
    except Exception as e:
        logger.error(f"Error checking/seeding club details: {e}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "club_scraped_data.json")
    seed_club_details(json_path)
