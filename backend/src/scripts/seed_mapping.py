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
        logger.info(f"Syncing competition_mapping from {csv_path}...")
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
                        ON CONFLICT (name) DO UPDATE SET
                            parent_competition = EXCLUDED.parent_competition,
                            division = EXCLUDED.division,
                            grade = EXCLUDED.grade
                    """),
                    {
                        "parent": row.get("Parent Competition"),
                        "name": row.get("Competition"),
                        "div": row.get("Divison") or row.get("Division"), # handle typo
                        "grade": row.get("Grade")
                    }
                )
                count += 1
        logger.info(f"Successfully synced {count} mapping entries.")
    
    # Also seed clubs from JSON if available
    script_dir = os.path.dirname(os.path.abspath(csv_path))
    json_path = os.path.join(script_dir, "parent_club.json")
    seed_clubs_from_json(json_path)

def seed_clubs_from_json(json_path: str):
    if not os.path.exists(json_path):
        logger.warning(f"JSON file not found: {json_path}")
        return
        
    import json
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    engine = get_engine()
    with engine.begin() as conn:
        count = 0
        for group in data:
            parent = group.get("Parent Competition")
            div = group.get("Division")
            clubs = group.get("Clubs", [])
            
            # Find a mapping for this group
            mapping_res = conn.execute(
                text("SELECT id FROM competition_mapping WHERE parent_competition = :p AND (division = :d OR (division IS NULL AND :d IS NULL)) LIMIT 1"),
                {"p": parent, "d": div}
            )
            mapping_id = mapping_res.scalar()
            if not mapping_id:
                continue
                
            for club_name in clubs:
                res = conn.execute(
                    text("UPDATE clubs SET competition_mapping_id = :mid WHERE name = :name AND competition_mapping_id IS NULL"),
                    {"mid": mapping_id, "name": club_name}
                )
                if res.rowcount > 0:
                    count += 1
        logger.info(f"Updated {count} clubs with mapping from JSON.")

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(script_dir, "competition_parent_mapping - Sheet1.csv")
    path = os.environ.get("MAPPING_CSV_PATH", default_path)
    seed_mapping(path)
    
    json_path = os.path.join(script_dir, "parent_club.json")
    seed_clubs_from_json(json_path)
