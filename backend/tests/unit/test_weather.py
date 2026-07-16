from datetime import datetime
import pytest
from unittest.mock import patch, AsyncMock
from src.weather.service import (
    round_to_nearest_hour,
    get_weather_for_appointment,
    fetch_hourly_weather,
)


def test_round_to_nearest_hour():
    # Test rounding down
    dt1 = datetime(2026, 7, 15, 15, 29, 0)
    assert round_to_nearest_hour(dt1) == datetime(2026, 7, 15, 15, 0, 0)

    # Test rounding up
    dt2 = datetime(2026, 7, 15, 15, 30, 0)
    assert round_to_nearest_hour(dt2) == datetime(2026, 7, 15, 16, 0, 0)

    # Test hour transition
    dt3 = datetime(2026, 7, 15, 23, 45, 0)
    assert round_to_nearest_hour(dt3) == datetime(2026, 7, 16, 0, 0, 0)


@pytest.mark.asyncio
@patch("src.weather.service.fetch_hourly_weather")
async def test_get_weather_for_appointment_success(mock_fetch):
    # Mock Open-Meteo API response
    mock_fetch.return_value = {
        "hourly": {
            "time": ["2026-07-15T15:00", "2026-07-15T16:00"],
            "temperature_2m": [18.5, 17.2],
            "precipitation_probability": [10, 45],
            "windspeed_10m": [15.0, 18.2],
        }
    }

    # Match time: 2026-07-15T15:35:00Z (UTC) -> rounds to 16:00 Sydney (UTC+10)
    # Wait, moment is parsed by parse_rx_moment_to_sydney.
    # If moment is 1784112000 (timestamp), let's just pass a naive datetime or timestamp.
    # 2026-07-15T05:35:00Z is 2026-07-15 15:35:00 in Sydney (UTC+10)
    # It rounds to 16:00 local time
    moment = "2026-07-15T05:35:00Z"

    res = await get_weather_for_appointment(-33.8791, 151.2581, moment)

    assert res is not None
    assert res["temperature"] == 17.2
    assert res["precipitation_probability"] == 45
    assert res["wind_speed"] == 18.2


@pytest.mark.asyncio
async def test_get_weather_for_appointment_missing_coords():
    res = await get_weather_for_appointment(None, 151.2581, "2026-07-15T15:00:00Z")
    assert res is None

    res = await get_weather_for_appointment(-33.8791, None, "2026-07-15T15:00:00Z")
    assert res is None
