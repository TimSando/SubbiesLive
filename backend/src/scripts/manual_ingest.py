import argparse
import logging
import os
import sys
from sqlalchemy.orm import sessionmaker

# Add src to the path so python can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.engine import get_sync_engine
from src.ingestion.service import run_ingestion
from src.ingestion.game_stats import SyncMode

# Configure logging to output directly to the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingestion")


def main():

    parser = argparse.ArgumentParser(description="Run manual data ingestion.")
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=[mode.value for mode in SyncMode],
        default=SyncMode.FAST.value,
        help="Sync mode: fast (default), recent, full, or live_only",
    )
    parser.add_argument(
        "--skip-notifications",
        action="store_true",
        help="Disable sending push notifications to devices",
    )
    args = parser.parse_args()

    if args.skip_notifications:
        os.environ["SKIP_NOTIFICATIONS"] = "true"

    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine)

    sync_mode = SyncMode(args.mode)
    print(f"Starting manual ingestion (mode: {sync_mode.value})...")
    run_ingestion(SessionLocal, sync_mode)
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
