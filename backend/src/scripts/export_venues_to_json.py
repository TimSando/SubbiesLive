import json
import os
import logging
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
from src.venues.models import Venue
import src.core.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("export_venues")


def export_venues():
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        venues = session.query(Venue).order_by(Venue.id).all()
        venues_list = []
        for v in venues:
            venues_list.append(
                {
                    "id": v.id,
                    "name": v.name,
                    "address": v.address,
                    "latitude": v.latitude,
                    "longitude": v.longitude,
                }
            )

        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "venues.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(venues_list, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully exported {len(venues_list)} venues to {json_path}")
    except Exception as e:
        logger.error(f"Failed to export venues: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    export_venues()
