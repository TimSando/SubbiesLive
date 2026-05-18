import os
from sqlalchemy import create_engine, text

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

def main():
    engine = get_engine()
    query = """
        SELECT DISTINCT c.id, c.name, comp.name AS comp_name
        FROM teams t
        JOIN clubs c ON t.club_id = c.id
        JOIN competitions comp ON t.competition_id = comp.id
        WHERE comp.name LIKE '%%Joy Johnson%%'
        ORDER BY c.name
    """
    with engine.connect() as conn:
        res = conn.execute(text(query)).fetchall()
        print("Clubs in Joy Johnson competitions:")
        for row in res:
            print(f"- Club ID: {row[0]}, Name: {row[1]}, Competition: {row[2]}")

if __name__ == "__main__":
    main()
