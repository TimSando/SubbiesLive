import os
import sys
import logging
from sqlalchemy.orm import sessionmaker

# Add backend root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.engine import get_sync_engine
from src.ratings.service import backfill_ratings
import src.core.models  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingestion")


def main():
    logger.info("Initializing Elo rating backfill...")
    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine)
    backfill_ratings(SessionLocal)
    logger.info("Elo rating backfill successfully completed!")


if __name__ == "__main__":
    main()
