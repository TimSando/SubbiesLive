"""Service to fetch weather data from Open-Meteo API."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
import httpx
from src.core.cache import ttl_cache
from src.refzone.matching import parse_rx_moment_to_sydney

logger = logging.getLogger("uvicorn")


def round_to_nearest_hour(dt: datetime) -> datetime:
    """Rounds a datetime object to the nearest hour."""
    if dt.minute >= 30:
        return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        return dt.replace(minute=0, second=0, microsecond=0)


@ttl_cache(ttl_seconds=10800)  # Cache for 3 hours
async def fetch_hourly_weather(
    latitude: float, longitude: float, date_str: str
) -> dict:
    """Fetches hourly weather data from Open-Meteo for a given lat/lon and date.

    Cached to avoid hitting external API repeatedly for the same venue/day.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,windspeed_10m",
        "timezone": "Australia/Sydney",
        "start_date": date_str,
        "end_date": date_str,
    }
    logger.info(
        f"Fetching weather from Open-Meteo: {latitude},{longitude} on {date_str}"
    )
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()


async def get_weather_for_appointment(
    latitude: Optional[float], longitude: Optional[float], moment: Any
) -> Optional[dict]:
    """Gets the temperature, precipitation probability, and wind speed for an appointment.

    Translates the match moment to Sydney local time, rounds to the nearest hour,
    fetches/caches the 24-hour weather data for that day, and extracts the hour's forecast.
    """
    if latitude is None or longitude is None or moment is None:
        return None

    syd_dt = parse_rx_moment_to_sydney(moment)
    if not syd_dt:
        return None

    date_str = syd_dt.strftime("%Y-%m-%d")
    nearest_hour = round_to_nearest_hour(syd_dt)
    target_time_str = nearest_hour.strftime("%Y-%m-%dT%H:00")

    try:
        data = await fetch_hourly_weather(latitude, longitude, date_str)
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if target_time_str in times:
            idx = times.index(target_time_str)

            # Helper to extract value safely
            def get_val(key):
                lst = hourly.get(key, [])
                return lst[idx] if idx < len(lst) else None

            return {
                "temperature": get_val("temperature_2m"),
                "precipitation_probability": get_val("precipitation_probability"),
                "wind_speed": get_val("windspeed_10m"),
            }
    except Exception as e:
        logger.warning(
            f"Failed to fetch weather for {latitude},{longitude} on {date_str}: {e}"
        )

    return None
