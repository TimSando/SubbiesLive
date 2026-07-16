import sys
import logging
import httpx
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
import src.venues.models
import src.games.models
import src.clubs.models
import src.competitions.models
import src.players.models
from src.venues.models import Venue
from src.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_venues_google_maps")


def geocode_google_maps(venue_name: str, api_key: str) -> tuple[float, float] | None:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    query = f"{venue_name}, Sydney, NSW, Australia"
    params = {"address": query, "key": api_key}
    try:
        # Use a synchronous HTTP client to query Google Maps
        with httpx.Client() as client:
            r = client.get(url, params=params, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "OK" and data.get("results"):
                    loc = data["results"][0]["geometry"]["location"]
                    return float(loc["lat"]), float(loc["lng"])
                else:
                    logger.warning(
                        f"Google Maps geocoding status not OK or empty results for '{query}': {data.get('status')}"
                    )
            else:
                logger.error(
                    f"Google Maps Geocoding API returned status code {r.status_code}"
                )
    except Exception as e:
        logger.error(f"Exception during Google Maps geocoding for '{query}': {e}")
    return None


def update_venues(commit: bool = False):
    settings = get_settings()
    api_key = settings.google_maps_api_key
    if not api_key:
        logger.error(
            "GOOGLE_MAPS_API_KEY is not set in the configuration or environment. Exiting."
        )
        sys.exit(1)

    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        venues = session.query(Venue).all()
        logger.info(f"Loaded {len(venues)} venues from database.")

        updated_count = 0
        failed_count = 0

        for venue in venues:
            logger.info(
                f"Geocoding: {venue.name} (Current: {venue.latitude}, {venue.longitude})"
            )
            coords = geocode_google_maps(venue.name, api_key)
            if coords:
                new_lat, new_lon = coords
                # Check if coordinates have changed or were None
                has_changes = False
                if venue.latitude is None or venue.longitude is None:
                    has_changes = True
                elif (
                    abs(venue.latitude - new_lat) > 1e-6
                    or abs(venue.longitude - new_lon) > 1e-6
                ):
                    has_changes = True

                if has_changes:
                    logger.info(
                        f"  -> Update found for '{venue.name}': "
                        f"({venue.latitude}, {venue.longitude}) -> ({new_lat}, {new_lon})"
                    )
                    venue.latitude = new_lat
                    venue.longitude = new_lon
                    updated_count += 1
                else:
                    logger.info(f"  -> No change for '{venue.name}'")
            else:
                logger.warning(f"  -> Failed to resolve coordinates for '{venue.name}'")
                failed_count += 1

        if commit:
            session.commit()
            logger.info(
                f"Successfully updated and committed {updated_count} venues. {failed_count} failed to resolve."
            )
        else:
            logger.info(
                f"DRY RUN: {updated_count} venues would be updated. Run with --commit to apply changes."
            )

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update venues via Google Maps: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    should_commit = "--commit" in sys.argv
    update_venues(commit=should_commit)
