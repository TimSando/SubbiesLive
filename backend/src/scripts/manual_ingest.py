import os
import sys
from sqlalchemy.orm import sessionmaker

# Add src to the path so python can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.engine import get_sync_engine
from src.ingestion.service import run_ingestion


def main():
    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine)

    print("Starting manual ingestion...")
    run_ingestion(SessionLocal)
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
