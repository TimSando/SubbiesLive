import csv
import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_mapping")

def get_engine():
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    )
    if not db_url or "+asyncpg" in db_url:
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_USER', 'subbiesstats')}"
            f":{os.environ.get('POSTGRES_PASSWORD', 'subbiesstats_dev_2026')}"
            f"@{os.environ.get('POSTGRES_HOST', 'db')}"
            f":5432/{os.environ.get('POSTGRES_DB', 'subbiesstats')}"
        )
    return create_engine(db_url)

def seed_mapping(csv_path: str):
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return

    engine = get_engine()
    with engine.begin() as conn:
        # Check if already seeded
        res = conn.execute(text("SELECT COUNT(*) FROM competition_mapping"))
        if res.scalar() > 0:
            logger.info("competition_mapping already contains data. Skipping seed.")
            return

        logger.info(f"Seeding competition_mapping from {csv_path}...")
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Map CSV headers to DB columns
            # CSV: Parent Competition, Competition, Divison, Grade
            # DB: parent_competition, name, division, grade
            count = 0
            for row in reader:
                conn.execute(
                    text("""
                        INSERT INTO competition_mapping (parent_competition, name, division, grade)
                        VALUES (:parent, :name, :div, :grade)
                        ON CONFLICT (name) DO NOTHING
                    """),
                    {
                        "parent": row.get("Parent Competition"),
                        "name": row.get("Competition"),
                        "div": row.get("Divison") or row.get("Division"), # handle typo
                        "grade": row.get("Grade")
                    }
                )
                count += 1
        logger.info(f"Successfully seeded {count} mapping entries.")

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(script_dir, "competition_parent_mapping - Sheet1.csv")
    path = os.environ.get("MAPPING_CSV_PATH", default_path)
    seed_mapping(path)
