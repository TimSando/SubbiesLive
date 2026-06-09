import pytest
import base64
from unittest.mock import AsyncMock, MagicMock
from src.refzone.router import fetch_fresh_rx_basic_token, CLIENT_SECRET_RE

pytestmark = pytest.mark.asyncio


async def test_client_secret_regex_matches_expected_format():
    sample = (
        'var j="auth",U="supersecretoken",F="3jz0nDldkPTDEpgJOb6myXNhL7Hx6N3Vs9xRGp72"'
    )
    match = CLIENT_SECRET_RE.search(sample)
    assert match is not None
    assert match.group(1) == "3jz0nDldkPTDEpgJOb6myXNhL7Hx6N3Vs9xRGp72"


async def test_fetch_fresh_token_builds_correct_base64():
    """End-to-end: regex match -> base64 encode -> correct output."""
    secret = "3jz0nDldkPTDEpgJOb6myXNhL7Hx6N3Vs9xRGp72CW5WL4RkVO"
    html = '<script src="/_next/static/chunks/pages/_app-abc123.js"></script>'
    chunk_content = f'var j="auth",U="supersecretoken",F="{secret}"'

    mock_login_page = MagicMock(status_code=200, text=html)
    mock_chunk = MagicMock(status_code=200, text=chunk_content)
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=[mock_login_page, mock_chunk])
    mock_login_page.raise_for_status = MagicMock()

    result = await fetch_fresh_rx_basic_token(mock_client)

    expected = base64.b64encode(f"auth:{secret}".encode()).decode()
    assert result == expected
