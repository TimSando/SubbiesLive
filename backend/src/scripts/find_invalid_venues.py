import logging
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
from src.venues.models import Venue
import src.core.models  # noqa: F401

logging.basicConfig(level=logging.INFO)


def list_venues():
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        venues = session.query(Venue).order_by(Venue.name).all()
        print(f"\nTotal venues in database: {len(venues)}")
        for v in venues:
            print(
                f"- ID: {v.id} | Name: '{v.name}' | Coords: ({v.latitude}, {v.longitude})"
            )
    finally:
        session.close()


if __name__ == "__main__":
    list_venues()
