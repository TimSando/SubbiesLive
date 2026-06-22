import pytest
import base64
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock

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

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "jwtTokens": {"accessToken": "new-access", "refreshToken": "new-refresh"}
    }

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
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

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "jwtTokens": {
            "accessToken": generate_mock_jwt(user_id="222"),
            "refreshToken": "new-refresh-tok",
        },
        "userId": "222",
    }

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
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

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "jwtTokens": {
            "accessToken": generate_mock_jwt(user_id="333"),
            "refreshToken": "new-refresh-tok",
        },
        "userId": "333",
    }

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        r = await client.get("/api/refzone/status")

    assert r.status_code == 200
    assert r.json() == {"authenticated": True, "userId": "333"}
    assert r.cookies.get("rx_refresh_token") == "new-refresh-tok"
