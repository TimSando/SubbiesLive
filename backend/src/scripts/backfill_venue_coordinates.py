"""Script to backfill latitude and longitude coordinates for venues using OpenStreetMap Nominatim API."""

import time
import logging
import httpx
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
from src.venues.models import Venue
import src.core.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_venues")


def safe_nominatim_request(client: httpx.Client, query: str) -> httpx.Response:
    """Make request to Nominatim API with 429 rate limit backoff and retries."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}

    retries = 3
    backoff = 10.0  # start with 10s sleep on 429

    for attempt in range(retries):
        try:
            r = client.get(url, params=params, timeout=10.0)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                logger.warning(
                    f"Received 429 Too Many Requests. Backing off for {backoff} seconds (attempt {attempt + 1}/{retries})..."
                )
                time.sleep(backoff)
                backoff *= 2  # exponential backoff
            else:
                return r
        except httpx.RequestError as e:
            logger.error(f"HTTP Request error: {e}")
            if attempt < retries - 1:
                time.sleep(2.0)
            else:
                raise

    raise RuntimeError(
        "Aborting backfill script: Stalled by persistent Nominatim 429 Rate Limits."
    )


def backfill_venues():
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query all venues without latitude
    venues = session.query(Venue).filter(Venue.latitude.is_(None)).all()
    logger.info(f"Found {len(venues)} venues with missing coordinates.")

    if not venues:
        logger.info("No venues to backfill.")
        return

    # Nominatim requires a custom User-Agent to avoid being blocked
    headers = {
        "User-Agent": "subbiesstats-geocoder/0.1.0 (admin@subbiesstats.calypsolab.xyz)"
    }

    client = httpx.Client(headers=headers)

    try:
        for venue in venues:
            # Construct search query
            # Sydney Subbies venues are in Sydney, NSW, Australia
            query = f"{venue.name}, Sydney, Australia"
            logger.info(f"Geocoding: {venue.name} (Query: '{query}')")

            try:
                r = safe_nominatim_request(client, query)
                if r.status_code == 200:
                    results = r.json()
                    if results:
                        lat = float(results[0]["lat"])
                        lon = float(results[0]["lon"])
                        venue.latitude = lat
                        venue.longitude = lon
                        logger.info(f"Success: {venue.name} -> lat={lat}, lon={lon}")
                        session.commit()
                        time.sleep(1.5)
                        continue

                    # Fallback query without "Sydney, Australia" in case it's a specific NSW region
                    logger.warning(
                        f"No results for '{query}'. Trying fallback: '{venue.name}, Australia'"
                    )
                    r_fallback = safe_nominatim_request(
                        client, f"{venue.name}, Australia"
                    )
                    if r_fallback.status_code == 200:
                        fallback_results = r_fallback.json()
                        if fallback_results:
                            lat = float(fallback_results[0]["lat"])
                            lon = float(fallback_results[0]["lon"])
                            venue.latitude = lat
                            venue.longitude = lon
                            logger.info(
                                f"Success (Fallback): {venue.name} -> lat={lat}, lon={lon}"
                            )
                            session.commit()
                            time.sleep(1.5)
                            continue

                    logger.warning(f"No coordinates found for {venue.name}")
                else:
                    logger.error(
                        f"Failed to geocode {venue.name}: Status {r.status_code}"
                    )

            except RuntimeError as re_err:
                logger.error(str(re_err))
                # Propagate to stop the script execution on persistent 429
                raise
            except Exception as e:
                logger.error(f"Error geocoding {venue.name}: {e}")

            # Strict Nominatim usage policy: 1 request per second max.
            time.sleep(1.5)

    except RuntimeError:
        logger.error("Script execution stopped due to rate limits.")
    finally:
        client.close()
        session.close()


if __name__ == "__main__":
    backfill_venues()
