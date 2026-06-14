import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to the path so python can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.service import ingest_player_history_for_game


def main():
    db_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        print("DATABASE_URL not set!")
        return

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Build team_id_map
    teams = session.execute(text("SELECT id, external_id, name FROM teams")).fetchall()
    team_id_map = {t[1]: t[0] for t in teams}
    print(f"Loaded {len(team_id_map)} teams into mapping.")

    # 2. Query completed UNSW games
    unsw_team_ids = (134, 148, 164, 170, 172, 252)
    query = text("""
        SELECT id, external_id, home_team_id, away_team_id 
        FROM games 
        WHERE status = 'completed' 
          AND (home_team_id IN :team_ids OR away_team_id IN :team_ids)
    """)
    games = session.execute(query, {"team_ids": unsw_team_ids}).fetchall()
    print(f"Found {len(games)} completed games involving UNSW.")

    # 3. Backfill
    for idx, game in enumerate(games):
        game_id = game[0]
        ext_game_id = game[1]
        print(
            f"[{idx+1}/{len(games)}] Backfilling game {game_id} (ext_id={ext_game_id})..."
        )
        try:
            ingest_player_history_for_game(session, game_id, ext_game_id, team_id_map)
        except Exception as e:
            print(f"  Error backfilling game {game_id}: {e}")

    print("Backfill complete!")


if __name__ == "__main__":
    main()
