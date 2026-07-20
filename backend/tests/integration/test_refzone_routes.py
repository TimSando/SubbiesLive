import pytest
import base64
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


# Helper to generate mock JWT tokens
def generate_mock_jwt(user_id="1", exp=None):
    if exp is None:
        exp = int(time.time()) + 3600
    header = (
        base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        .decode()
        .strip("=")
    )
    payload = (
        base64.b64encode(json.dumps({"userId": user_id, "exp": exp}).encode())
        .decode()
        .strip("=")
    )
    return f"{header}.{payload}.signature"


async def test_rx_login_mfa_required(client):
    """If RX login response requires MFA, extract challenge token and return mfa_required status."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"isMfaEnabled": True, "token": "challenge-jwt-xyz"}

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        r = await client.post(
            "/api/refzone/login", json={"email": "a@b.com", "password": "pw"}
        )

    assert r.status_code == 200
    assert r.json() == {"status": "mfa_required", "mfa_token": "challenge-jwt-xyz"}
    # Cookies should NOT be set
    assert "rx_access_token" not in r.cookies
    assert "rx_refresh_token" not in r.cookies


async def test_rx_login_succeeds_no_mfa(client):
    """If RX login response does not require MFA (direct success), set cookies and return ok status."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "jwtTokens": {"accessToken": "access-tok", "refreshToken": "refresh-tok"},
        "userId": "100",
    }

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        r = await client.post(
            "/api/refzone/login", json={"email": "a@b.com", "password": "pw"}
        )

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "userId": "100"}
    assert r.cookies.get("rx_access_token") == "access-tok"
    assert r.cookies.get("rx_refresh_token") == "refresh-tok"


async def test_rx_login_retries_on_stale_token(client):
    """First attempt fails -> scrape triggers -> retry succeeds."""
    fail = MagicMock(status_code=500, text="Server Error")
    success = MagicMock(status_code=200)
    success.json.return_value = {"isMfaEnabled": True, "token": "challenge-jwt-xyz"}

    with patch(
        "src.refzone.router.fetch_fresh_rx_basic_token", new_callable=AsyncMock
    ) as mock_scrape:
        mock_scrape.return_value = "newbase64token=="
        with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[fail, success]
            )
            r = await client.post(
                "/api/refzone/login", json={"email": "a@b.com", "password": "pw"}
            )

    mock_scrape.assert_awaited_once()
    assert r.status_code == 200
    assert r.json() == {"status": "mfa_required", "mfa_token": "challenge-jwt-xyz"}


async def test_rx_login_returns_401_for_bad_credentials(client):
    """Valid token, wrong user credentials -> propagate 401."""
    mock_resp = MagicMock(
        status_code=401, text='{"message":"Incorrect email or password"}'
    )

    with patch("src.refzone.router.fetch_fresh_rx_basic_token", new_callable=AsyncMock):
        with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            r = await client.post(
                "/api/refzone/login",
                json={"email": "bad@test.com", "password": "wrong"},
            )

    assert r.status_code == 401


async def test_verify_2fa_success(client):
    """Verify 2FA accepts token and code, constructs basic auth header, sets cookies, and strips jwtTokens."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "jwtTokens": {
            "accessToken": "access-tok-mfa",
            "refreshToken": "refresh-tok-mfa",
        },
        "userId": "100",
        "email": "user@test.com",
    }

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value.__aenter__.return_value.post = mock_post

        r = await client.post(
            "/api/refzone/verify-2fa", json={"token": "challenge-jwt", "code": "123456"}
        )

    assert r.status_code == 200
    assert r.json() == {"userId": "100", "email": "user@test.com"}
    assert r.cookies.get("rx_access_token") == "access-tok-mfa"
    assert r.cookies.get("rx_refresh_token") == "refresh-tok-mfa"

    # Assert correct header was constructed
    called_headers = mock_post.call_args[1]["headers"]
    expected_basic_raw = "challenge-jwt:123456"
    expected_basic_val = base64.b64encode(expected_basic_raw.encode()).decode()
    assert called_headers["Authorization"] == f"Basic {expected_basic_val}"


async def test_verify_2fa_returns_401_on_wrong_code(client):
    """If RX verify responds with error, propagate status code."""
    mock_resp = MagicMock(status_code=401, text="Invalid code")

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        r = await client.post(
            "/api/refzone/verify-2fa", json={"token": "challenge-jwt", "code": "000000"}
        )

    assert r.status_code == 401


async def test_status_returns_authenticated_with_valid_cookie(client):
    """If cookie has valid JWT, status endpoint returns authenticated=True and userId."""
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    r = await client.get("/api/refzone/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": True, "userId": "123"}


async def test_status_returns_unauthenticated_without_cookie(client):
    """If cookie is absent, status endpoint returns authenticated=False."""
    # Ensure no cookie
    if "rx_access_token" in client.cookies:
        del client.cookies["rx_access_token"]

    r = await client.get("/api/refzone/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False, "userId": None}


async def test_status_returns_unauthenticated_with_expired_cookie(client):
    """If cookie contains expired JWT, status endpoint returns authenticated=False."""
    jwt_tok = generate_mock_jwt(user_id="123", exp=int(time.time()) - 10)
    client.cookies.set("rx_access_token", jwt_tok)

    r = await client.get("/api/refzone/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False, "userId": None}


async def test_refresh_sets_new_cookies(client):
    """POST /refresh reads refresh cookie, calls RX refresh, and updates cookies."""
    client.cookies.set("rx_refresh_token", "old-refresh-tok")

    payload = {
        "jwtTokens": {"accessToken": "new-access", "refreshToken": "new-refresh"}
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_resp
        )
        r = await client.post("/api/refzone/refresh")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.cookies.get("rx_access_token") == "new-access"
    assert r.cookies.get("rx_refresh_token") == "new-refresh"


async def test_refresh_returns_401_without_cookie(client):
    """POST /refresh returns 401 if refresh cookie is missing."""
    if "rx_refresh_token" in client.cookies:
        del client.cookies["rx_refresh_token"]

    r = await client.post("/api/refzone/refresh")
    assert r.status_code == 401


async def test_logout_clears_cookies(client):
    """POST /logout deletes access and refresh cookies."""
    client.cookies.set("rx_access_token", "access")
    client.cookies.set("rx_refresh_token", "refresh")

    r = await client.post("/api/refzone/logout")
    assert r.status_code == 200
    assert r.json() == {"status": "logged_out"}

    # In httpx TestClient, deleted cookies have empty values or are removed
    assert not r.cookies.get("rx_access_token")
    assert not r.cookies.get("rx_refresh_token")


async def test_appointments_requires_cookie(client):
    """Appointments endpoint returns 401 when access token cookie is missing."""
    if "rx_access_token" in client.cookies:
        del client.cookies["rx_access_token"]

    r = await client.get("/api/refzone/appointments", params={"userId": "123"})
    assert r.status_code == 401


async def test_get_profile_requires_cookie(client):
    """Profile endpoint returns 401 when access token cookie is missing."""
    if "rx_access_token" in client.cookies:
        del client.cookies["rx_access_token"]

    r = await client.get("/api/refzone/profile", params={"userId": "123"})
    assert r.status_code == 401


async def test_get_profile_serves_from_cache(client):
    """Profile endpoint returns profile from cache if present, without downstream call."""
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_profile = {
        "firstname": "Timothy",
        "lastname": "Sanderson",
        "headshot": "https://test.com/img.png",
    }

    from src.refzone.router import _cached_profiles

    _cached_profiles["123"] = mock_profile

    try:
        # Patch httpx AsyncClient to verify no request is made
        with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
            r = await client.get("/api/refzone/profile", params={"userId": "123"})
            mock_cls.assert_not_called()

        assert r.status_code == 200
        assert r.json() == mock_profile
    finally:
        _cached_profiles.pop("123", None)


async def test_get_profile_requests_downstream_and_caches(client):
    """Profile endpoint calls downstream if not cached, then caches response."""
    jwt_tok = generate_mock_jwt(user_id="456")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_profile = {
        "firstname": "Test",
        "lastname": "User",
        "headshot": "https://test.com/user.png",
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = mock_profile

    from src.refzone.router import _cached_profiles

    _cached_profiles.pop("456", None)

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_resp
        )
        r = await client.get("/api/refzone/profile", params={"userId": "456"})

    assert r.status_code == 200
    assert r.json() == mock_profile
    assert _cached_profiles.get("456") == mock_profile
    _cached_profiles.pop("456", None)


async def test_get_profile_fails_downstream_uses_fallback(client):
    """Profile endpoint returns a default fallback profile when RugbyXplorer request fails."""
    jwt_tok = generate_mock_jwt(user_id="789")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_resp = MagicMock(status_code=400, text="Bad Request -> Invalid National Id")

    from src.refzone.router import _cached_profiles

    _cached_profiles.pop("789", None)

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_resp
        )
        r = await client.get("/api/refzone/profile", params={"userId": "789"})

    assert r.status_code == 200
    assert r.json() == {"firstname": "Referee", "lastname": "", "headshot": ""}
    assert "789" not in _cached_profiles


async def test_logout_invalidates_cache(client):
    """POST /logout clears the user profile from in-memory cache."""
    jwt_tok = generate_mock_jwt(user_id="111")
    client.cookies.set("rx_access_token", jwt_tok)

    from src.refzone.router import _cached_profiles

    _cached_profiles["111"] = {"firstname": "Timothy"}

    r = await client.post("/api/refzone/logout")
    assert r.status_code == 200
    assert "111" not in _cached_profiles


async def test_status_endpoint_silent_refresh_on_missing_access_token(client):
    """If access token is missing but refresh token is present, /status performs a silent refresh."""
    client.cookies.set("rx_refresh_token", "valid-refresh-tok")

    payload = {
        "jwtTokens": {
            "accessToken": generate_mock_jwt(user_id="222"),
            "refreshToken": "new-refresh-tok",
        },
        "userId": "222",
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_resp
        )
        r = await client.get("/api/refzone/status")

    assert r.status_code == 200
    assert r.json() == {"authenticated": True, "userId": "222"}
    assert "rx_access_token" in r.cookies
    assert r.cookies.get("rx_refresh_token") == "new-refresh-tok"


async def test_status_endpoint_silent_refresh_on_expired_access_token(client):
    """If access token is expired but refresh token is present, /status performs a silent refresh."""
    expired_jwt = generate_mock_jwt(user_id="333", exp=int(time.time()) - 10)
    client.cookies.set("rx_access_token", expired_jwt)
    client.cookies.set("rx_refresh_token", "valid-refresh-tok")

    payload = {
        "jwtTokens": {
            "accessToken": generate_mock_jwt(user_id="333"),
            "refreshToken": "new-refresh-tok",
        },
        "userId": "333",
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = json.dumps(payload)
    mock_resp.json.return_value = payload

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_resp
        )
        r = await client.get("/api/refzone/status")

    assert r.status_code == 200
    assert r.json() == {"authenticated": True, "userId": "333"}
    assert r.cookies.get("rx_refresh_token") == "new-refresh-tok"


async def test_appointments_game_linking(client, db_session):
    """Verify that appointments endpoint matches games and sets db_game_id."""
    from src.venues.models import Venue
    from src.games.models import Game
    from src.clubs.models import Club, Team
    from src.competitions.models import Competition, Round
    from datetime import datetime

    # Setup database records for matching game
    comp = Competition(name="Kentwell Cup", external_id=1001)
    db_session.add(comp)
    await db_session.flush()

    rnd = Round(competition_id=comp.id, name="Round 1", external_id=2001)
    db_session.add(rnd)
    await db_session.flush()

    club_home = Club(name="Colleagues")
    club_away = Club(name="Mosman")
    db_session.add_all([club_home, club_away])
    await db_session.flush()

    team_home = Team(
        club_id=club_home.id,
        name="Colleagues",
        competition_id=comp.id,
        external_id=3001,
    )
    team_away = Team(
        club_id=club_away.id, name="Mosman", competition_id=comp.id, external_id=3002
    )
    db_session.add_all([team_home, team_away])
    await db_session.flush()

    game = Game(
        round_id=rnd.id,
        home_team_id=team_home.id,
        away_team_id=team_away.id,
        game_date=datetime(2026, 7, 16, 1, 30, 0),
        external_id=5001,
    )
    db_session.add(game)
    await db_session.commit()

    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_appointment = {
        "_id": "app-1",
        "status": "pending",
        "isActive": True,
        "type": "Referee",
        "match": {
            "moment": "2026-07-15T15:30:00.000Z",
            "homeTeam": {"name": "Colleagues"},
            "awayTeam": {"name": "Mosman"},
            "competition": {"name": "Kentwell Cup"},
            "venue": {"name": "Forsyth Park"},
        },
    }

    confirmed_resp = MagicMock(status_code=200)
    confirmed_resp.json.return_value = [mock_appointment]
    pending_resp = MagicMock(status_code=200)
    pending_resp.json.return_value = []

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=[confirmed_resp, pending_resp]
        )

        r = await client.get("/api/refzone/appointments", params={"userId": "123"})

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["db_game_id"] == game.id


async def test_venue_weather_existing_venue(client, db_session):
    """Verify that venue-weather endpoint resolves an existing venue and returns coordinates and weather."""
    from src.venues.models import Venue

    # Add venue to DB
    venue = Venue(name="Forsyth Park", latitude=-33.8340, longitude=151.2140)
    db_session.add(venue)
    await db_session.commit()

    mock_weather = {
        "temperature": 18.5,
        "precipitation_probability": 10,
        "wind_speed": 15.0,
    }

    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    with patch(
        "src.refzone.router.get_weather_for_appointment", new_callable=AsyncMock
    ) as mock_get_weather:
        mock_get_weather.return_value = mock_weather

        r = await client.get(
            "/api/refzone/venue-weather",
            params={
                "venue_name": "Forsyth Park",
                "moment": "2026-07-15T15:30:00.000Z",
            },
        )

    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == -33.8340
    assert data["longitude"] == 151.2140
    assert data["weather"] == mock_weather


async def test_venue_weather_db_game_fallback(client, db_session):
    """Verify that venue-weather endpoint falls back to matched game's venue if missing coords."""
    from src.venues.models import Venue
    from src.games.models import Game
    from src.clubs.models import Club, Team
    from src.competitions.models import Competition, Round
    from datetime import datetime

    # 1. Create a venue with coordinates
    known_venue = Venue(name="Known Oval", latitude=-33.1111, longitude=151.2222)
    db_session.add(known_venue)
    await db_session.flush()

    comp = Competition(name="Subbies", external_id=1002)
    db_session.add(comp)
    await db_session.flush()
    rnd = Round(competition_id=comp.id, name="R1", external_id=2002)
    db_session.add(rnd)
    await db_session.flush()
    club_h = Club(name="Club A")
    club_a = Club(name="Club B")
    db_session.add_all([club_h, club_a])
    await db_session.flush()
    team_h = Team(
        club_id=club_h.id, name="Team A", competition_id=comp.id, external_id=4001
    )
    team_a = Team(
        club_id=club_a.id, name="Team B", competition_id=comp.id, external_id=4002
    )
    db_session.add_all([team_h, team_a])
    await db_session.flush()

    # Create game with known venue
    game = Game(
        round_id=rnd.id,
        home_team_id=team_h.id,
        away_team_id=team_a.id,
        game_date=datetime(2026, 7, 15, 15, 30, 0),
        venue_id=known_venue.id,
        external_id=5002,
    )
    db_session.add(game)
    await db_session.commit()

    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    with patch(
        "src.refzone.router.get_weather_for_appointment", new_callable=AsyncMock
    ) as mock_get_weather:
        mock_get_weather.return_value = None

        r = await client.get(
            "/api/refzone/venue-weather",
            params={
                "venue_name": "New Unresolved Venue",
                "moment": "2026-07-15T15:30:00.000Z",
                "db_game_id": game.id,
            },
        )

    assert r.status_code == 200
    data = r.json()
    # It should copy coordinates from the matched game's venue
    assert data["latitude"] == -33.1111
    assert data["longitude"] == 151.2222

    # Check that a new Venue was created in DB for "New Unresolved Venue"
    res = await db_session.execute(
        select(Venue).where(Venue.name == "New Unresolved Venue")
    )
    new_venue = res.scalar_one_or_none()
    assert new_venue is not None
    assert new_venue.latitude == -33.1111


async def test_venue_weather_geocoding_lookup(client, db_session):
    """Verify that venue-weather endpoint calls Nominatim geocoding for unknown venues and saves coordinates."""
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_settings = MagicMock()
    mock_settings.google_maps_api_key = None

    mock_nominatim_resp = MagicMock(status_code=200)
    mock_nominatim_resp.json.return_value = [{"lat": "-33.9999", "lon": "151.8888"}]

    from src.venues.models import Venue

    with patch("src.refzone.router.get_settings", return_value=mock_settings):
        with patch(
            "src.refzone.router.safe_nominatim_request_async", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_nominatim_resp

            with patch(
                "src.refzone.router.get_weather_for_appointment", new_callable=AsyncMock
            ) as mock_get_weather:
                mock_get_weather.return_value = None

                r = await client.get(
                    "/api/refzone/venue-weather",
                    params={
                        "venue_name": "Mysterious Park",
                        "moment": "2026-07-15T15:30:00.000Z",
                    },
                )

    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == -33.9999
    assert data["longitude"] == 151.8888

    # Check that new venue was saved to database
    res = await db_session.execute(select(Venue).where(Venue.name == "Mysterious Park"))
    venue = res.scalar_one_or_none()
    assert venue is not None
    assert venue.latitude == -33.9999
    assert venue.longitude == 151.8888


async def test_venue_weather_geocoding_lookup_google_maps_success(client, db_session):
    """Verify that venue-weather endpoint queries Google Maps geocoding when API key is set and saves coordinates."""
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_settings = MagicMock()
    mock_settings.google_maps_api_key = "fake-gmaps-key"

    mock_gmaps_resp = MagicMock(status_code=200)
    mock_gmaps_resp.json.return_value = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": -33.7777, "lng": 151.7777}}}],
    }

    from src.venues.models import Venue

    with patch("src.refzone.router.get_settings", return_value=mock_settings):
        with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_gmaps_resp
            mock_cls.return_value.__aenter__.return_value = mock_client

            with patch(
                "src.refzone.router.get_weather_for_appointment", new_callable=AsyncMock
            ) as mock_get_weather:
                mock_get_weather.return_value = None

                r = await client.get(
                    "/api/refzone/venue-weather",
                    params={
                        "venue_name": "Google Park",
                        "moment": "2026-07-15T15:30:00.000Z",
                    },
                )

    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == -33.7777
    assert data["longitude"] == 151.7777

    # Check that new venue was saved to database
    res = await db_session.execute(select(Venue).where(Venue.name == "Google Park"))
    venue = res.scalar_one_or_none()
    assert venue is not None
    assert venue.latitude == -33.7777
    assert venue.longitude == 151.7777


async def test_venue_weather_geocoding_lookup_google_maps_fallback_to_nominatim(
    client, db_session
):
    """Verify that venue-weather endpoint falls back to Nominatim when Google Maps geocoding fails."""
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    mock_settings = MagicMock()
    mock_settings.google_maps_api_key = "fake-gmaps-key"

    # Nominatim succeeds
    mock_nominatim_resp = MagicMock(status_code=200)
    mock_nominatim_resp.json.return_value = [{"lat": "-33.6666", "lon": "151.6666"}]

    from src.venues.models import Venue

    # We patch safe_nominatim_request_async to return the mock Nominatim response
    with patch("src.refzone.router.get_settings", return_value=mock_settings):
        with patch(
            "src.refzone.router.google_maps_geocode_async", new_callable=AsyncMock
        ) as mock_gmaps_geocode:
            mock_gmaps_geocode.return_value = None

            with patch(
                "src.refzone.router.safe_nominatim_request_async",
                new_callable=AsyncMock,
            ) as mock_nominatim:
                mock_nominatim.return_value = mock_nominatim_resp

                with patch(
                    "src.refzone.router.get_weather_for_appointment",
                    new_callable=AsyncMock,
                ) as mock_get_weather:
                    mock_get_weather.return_value = None

                    r = await client.get(
                        "/api/refzone/venue-weather",
                        params={
                            "venue_name": "Fallback Park",
                            "moment": "2026-07-15T15:30:00.000Z",
                        },
                    )

    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == -33.6666
    assert data["longitude"] == 151.6666

    # Check that new venue was saved to database
    res = await db_session.execute(select(Venue).where(Venue.name == "Fallback Park"))
    venue = res.scalar_one_or_none()
    assert venue is not None
    assert venue.latitude == -33.6666
    assert venue.longitude == 151.6666


async def test_weather_endpoint_returns_forecast(client):
    """Verify that the weather endpoint invokes the service and returns forecast data."""
    mock_weather = {
        "temperature": 18.5,
        "precipitation_probability": 10,
        "wind_speed": 15.0,
    }

    # Setup token cookie (if route requires auth, wait, does /weather require auth?
    # No, it does not require auth cookies in our endpoint definition, but setting it is safe)
    jwt_tok = generate_mock_jwt(user_id="123")
    client.cookies.set("rx_access_token", jwt_tok)

    with patch(
        "src.refzone.router.get_weather_for_appointment", new_callable=AsyncMock
    ) as mock_get_weather:
        mock_get_weather.return_value = mock_weather

        r = await client.get(
            "/api/refzone/weather",
            params={
                "latitude": -33.8340,
                "longitude": 151.2140,
                "moment": "2026-07-15T15:30:00.000Z",
            },
        )

    assert r.status_code == 200
    assert r.json() == mock_weather
