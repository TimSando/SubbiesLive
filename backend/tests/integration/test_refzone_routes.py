import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.asyncio


async def test_rx_login_succeeds(client):
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"jwtTokens": {"accessToken": "tok"}, "userId": "1"}

    with patch("src.refzone.router.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        r = await client.post(
            "/api/refzone/login", json={"email": "a@b.com", "password": "pw"}
        )

    assert r.status_code == 200
    assert r.json()["userId"] == "1"


async def test_rx_login_retries_on_stale_token(client):
    """First attempt fails -> scrape triggers -> retry succeeds."""
    fail = MagicMock(status_code=500, text="Server Error")
    success = MagicMock(status_code=200)
    success.json.return_value = {"jwtTokens": {"accessToken": "tok"}, "userId": "1"}

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


async def test_appointments_requires_auth(client):
    r = await client.get("/api/refzone/appointments", params={"userId": "123"})
    assert r.status_code == 401
