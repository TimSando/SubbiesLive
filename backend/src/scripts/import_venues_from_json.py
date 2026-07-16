import json
import os
import sys
import logging
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
from src.venues.models import Venue
from src.games.models import Game
from src.clubs.models import Club
import src.core.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("import_venues")


def import_venues(commit: bool = False):
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "venues.json")

        if not os.path.exists(json_path):
            logger.error(f"Venues file not found at {json_path}")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            venues_list = json.load(f)

        logger.info(f"Loaded {len(venues_list)} venues from JSON file.")

        updated_count = 0
        inserted_count = 0

        for item in venues_list:
            venue_id = item.get("id")
            name = item.get("name")
            address = item.get("address")
            latitude = item.get("latitude")
            longitude = item.get("longitude")

            if not name:
                logger.warning("Skipping item with missing name.")
                continue

            # Try to find by id first
            v = None
            if venue_id is not None:
                v = session.query(Venue).get(venue_id)

            # If not found by id, try by name
            if v is None:
                v = session.query(Venue).filter(Venue.name == name).first()

            if v:
                # Update existing venue
                has_changes = False
                if v.name != name:
                    v.name = name
                    has_changes = True
                if v.address != address:
                    v.address = address
                    has_changes = True
                if v.latitude != latitude:
                    v.latitude = latitude
                    has_changes = True
                if v.longitude != longitude:
                    v.longitude = longitude
                    has_changes = True

                if has_changes:
                    updated_count += 1
                    logger.info(f"Updated venue: {name} (ID: {v.id})")
            else:
                # Insert new venue
                new_v = Venue(
                    name=name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                )
                if venue_id is not None:
                    new_v.id = venue_id
                session.add(new_v)
                inserted_count += 1
                logger.info(f"Prepared new venue to insert: {name}")

        # Flush session to ensure new/updated venues are visible in query
        session.flush()

        # Find venues missing latitude or longitude
        junk_venues = (
            session.query(Venue)
            .filter((Venue.latitude.is_(None)) | (Venue.longitude.is_(None)))
            .all()
        )
        deleted_count = len(junk_venues)

        if deleted_count > 0:
            logger.info(
                f"Found {deleted_count} junk venues (missing coordinates) to delete."
            )
            for jv in junk_venues:
                # Nullify references in games and clubs
                session.query(Game).filter(Game.venue_id == jv.id).update(
                    {Game.venue_id: None}
                )
                session.query(Club).filter(Club.primary_venue_id == jv.id).update(
                    {Club.primary_venue_id: None}
                )
                session.delete(jv)
                logger.info(f"Prepared to delete junk venue: {jv.name} (ID: {jv.id})")

        if commit:
            session.commit()
            logger.info(
                f"Successfully committed changes: {updated_count} updated, {inserted_count} inserted, {deleted_count} deleted."
            )
        else:
            logger.info(
                f"DRY RUN: {updated_count} venues would be updated, {inserted_count} venues would be inserted, {deleted_count} venues would be deleted. Run with --commit to apply changes."
            )

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to import/clean venues: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    should_commit = "--commit" in sys.argv
    import_venues(commit=should_commit)
