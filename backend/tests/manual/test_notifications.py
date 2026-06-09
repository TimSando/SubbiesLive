# Import central model registry first to register all models with SQLAlchemy
import src.core.models  # noqa: F401
import time

from sqlalchemy.orm import Session
from src.ingestion.engine import get_sync_engine
from src.notifications.service import notify_game_update
from src.games.models import Game
from sqlalchemy import select


def main():
    engine = get_sync_engine()
    with Session(engine) as session:
        # Find a game to mock
        game = session.execute(select(Game).limit(1)).scalar()
        if not game:
            print(
                "❌ No games found in the database. Please run ingestion or add mock games first."
            )
            return

        print(
            f"🔔 Subscribing to Game ID {game.id} or its associated Club/Competition in your PWA to test."
        )
        print(f"Triggering mock notification for Game ID: {game.id}...")

        # This will trigger notifications for anyone subscribed to:
        # - This specific game
        # - The home or away clubs playing in this game
        # - The competition of this game
        notify_game_update(
            session=session,
            game_id=game.id,
            update_type="outcome",
            detail_message=f"🏉 Test outcome notification! Full Time score update for Game ID {game.id}.",
        )
        print("Waiting 3 seconds for background threads to complete...")
        time.sleep(3)
        print("✅ Mock notification triggered successfully.")


if __name__ == "__main__":
    main()
