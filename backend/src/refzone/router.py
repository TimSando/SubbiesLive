import logging
import re
import base64
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter()
logger = logging.getLogger("uvicorn")

RX_BASE_URL = "https://api.rugbyxplorer.com.au"
RX_AUTH_PAGE = "https://auth.rugbyxplorer.com.au"
CLIENT_SECRET_RE = re.compile(
    r'["\']auth["\'],\s*\w+=\s*["\']supersecretoken["\'],\s*\w+=\s*["\']([A-Za-z0-9]{40,60})["\']'
)
SKIP_CHUNK_PREFIXES = (
    "polyfills",
    "webpack",
    "framework",
    "main",
    "_buildManifest",
    "_ssgManifest",
)

# In-memory cache for RugbyXplorer basic authorization token (base64 portion only)
_cached_basic_token: str = (
    "YXV0aDozanowbkRsZGtQVERFcGdKT2I2bXlYTmhMN0h4Nk4zVnM5eFJHcDcyQ1c1V0w0UmtWTw=="
)


class LoginRequest(BaseModel):
    email: str
    password: str


async def fetch_fresh_rx_basic_token(client: httpx.AsyncClient) -> str:
    """Scrapes the RugbyXplorer auth page to extract the current Basic auth token."""
    logger.info("Scraping RugbyXplorer auth page for fresh basic token...")
    login_page = await client.get(
        f"{RX_AUTH_PAGE}/login", params={"clientId": "portal"}, timeout=10.0
    )
    login_page.raise_for_status()

    # Extract JS chunk URLs from the HTML
    chunk_urls = re.findall(r'src="([^"]*_next/static/[^"]+\.js)"', login_page.text)

    # Skip framework/polyfill chunks that won't contain the token
    candidate_chunks = [
        u
        for u in chunk_urls
        if not any(Path(u).name.startswith(p) for p in SKIP_CHUNK_PREFIXES)
    ]

    for chunk_path in candidate_chunks:
        # Resolve full URL
        if chunk_path.startswith("http://") or chunk_path.startswith("https://"):
            url = chunk_path
        elif chunk_path.startswith("/"):
            url = f"{RX_AUTH_PAGE}{chunk_path}"
        else:
            url = f"{RX_AUTH_PAGE}/{chunk_path}"

        logger.info(f"Checking chunk: {url}")
        try:
            chunk_res = await client.get(url, timeout=10.0)
            if chunk_res.status_code != 200:
                continue
            match = CLIENT_SECRET_RE.search(chunk_res.text)
            if match:
                secret = match.group(1)
                logger.info("Found fresh RugbyXplorer client secret in chunk.")
                raw_auth = f"auth:{secret}"
                fresh_token = base64.b64encode(raw_auth.encode("utf-8")).decode("utf-8")
                return fresh_token
        except Exception as chunk_err:
            logger.warning(f"Error fetching chunk {url}: {chunk_err}")
            continue

    raise RuntimeError("Could not extract Basic auth token from RugbyXplorer auth page")


def get_rx_headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "clientId": "portal",
        "Content-Type": "application/json",
        "Origin": "https://auth.rugbyxplorer.com.au",
        "Referer": "https://auth.rugbyxplorer.com.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["Authorization"] = f"Basic {_cached_basic_token}"
    return headers


@router.post("/login")
async def rx_login(body: LoginRequest):
    global _cached_basic_token
    url = f"{RX_BASE_URL}/rau/api/v3/login"
    payload = {
        "email": body.email,
        "encodedParams": ["email", "password"],
        "password": body.password,
        "samlRequest": {},
    }

    async with httpx.AsyncClient() as client:
        try:
            headers = get_rx_headers()
            r = await client.post(url, json=payload, headers=headers, timeout=10.0)

            if r.status_code != 200:
                logger.warning(
                    f"RX Login failed (status={r.status_code}), attempting basic token refresh..."
                )
                try:
                    fresh_token = await fetch_fresh_rx_basic_token(client)
                    _cached_basic_token = fresh_token
                    headers = get_rx_headers()
                    r = await client.post(
                        url, json=payload, headers=headers, timeout=10.0
                    )
                except Exception as refresh_err:
                    logger.error(f"RX basic token refresh/retry failed: {refresh_err}")

            if r.status_code != 200:
                logger.error(
                    f"RX Login failed after retry: status={r.status_code}, response={r.text}"
                )
                raise HTTPException(
                    status_code=r.status_code, detail=f"Login failed: {r.text}"
                )

            return r.json()
        except httpx.RequestError as exc:
            logger.error(f"RX API error: {exc}")
            raise HTTPException(
                status_code=503, detail="RugbyXplorer service unavailable"
            )


from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import aliased
from src.core.dependencies import DbSession
from src.games.models import Game
from src.clubs.models import Team
from src.competitions.models import Competition, Round
from src.refzone.matching import parse_rx_moment_to_sydney, find_matching_game

HomeTeam = aliased(Team, name="home_team")
AwayTeam = aliased(Team, name="away_team")


@router.get("/appointments")
async def get_appointments(
    userId: str, db: DbSession, authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ")[1]
    headers = get_rx_headers(token)

    confirmed_url = f"{RX_BASE_URL}/rau/api/v3/appointments/user/{userId}"
    pending_url = f"{confirmed_url}?pending=true"

    async with httpx.AsyncClient() as client:
        try:
            # Fetch confirmed
            confirmed_res = await client.get(
                confirmed_url, headers=headers, timeout=10.0
            )
            if confirmed_res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif confirmed_res.status_code != 200:
                raise HTTPException(
                    status_code=confirmed_res.status_code,
                    detail="Failed to fetch confirmed appointments",
                )

            # Fetch pending
            pending_res = await client.get(pending_url, headers=headers, timeout=10.0)
            if pending_res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif pending_res.status_code != 200:
                raise HTTPException(
                    status_code=pending_res.status_code,
                    detail="Failed to fetch pending appointments",
                )

            confirmed_data = confirmed_res.json()
            pending_data = pending_res.json()

            # Combine appointments
            appointments = []
            if isinstance(confirmed_data, list):
                for app in confirmed_data:
                    appointments.append(app)

            if isinstance(pending_data, list):
                for app in pending_data:
                    # Make sure status is set/normalized
                    if "status" not in app:
                        app["status"] = "pending"
                    appointments.append(app)

            # Perform game linking matching
            if appointments:
                sydney_times = []
                for app in appointments:
                    if app.get("match") and app["match"].get("moment"):
                        syd_dt = parse_rx_moment_to_sydney(app["match"]["moment"])
                        if syd_dt:
                            app["match"]["sydney_moment"] = syd_dt
                            sydney_times.append(syd_dt)

                if sydney_times:
                    min_time = min(sydney_times) - timedelta(days=1)
                    max_time = max(sydney_times) + timedelta(days=1)

                    stmt = (
                        select(
                            Game.id,
                            Game.game_date,
                            HomeTeam.name.label("home_team_name"),
                            AwayTeam.name.label("away_team_name"),
                            Competition.name.label("competition_name"),
                        )
                        .join(Round, Round.id == Game.round_id)
                        .join(Competition, Competition.id == Round.competition_id)
                        .join(HomeTeam, HomeTeam.id == Game.home_team_id)
                        .join(AwayTeam, AwayTeam.id == Game.away_team_id)
                        .where(Game.game_date >= min_time)
                        .where(Game.game_date <= max_time)
                    )
                    res = await db.execute(stmt)
                    db_games = [
                        {
                            "id": row.id,
                            "game_date": row.game_date,
                            "home_team_name": row.home_team_name,
                            "away_team_name": row.away_team_name,
                            "competition_name": row.competition_name,
                        }
                        for row in res.all()
                    ]

                    for app in appointments:
                        if not app.get("match"):
                            continue

                        syd_dt = app["match"].get("sydney_moment")
                        home_team = app["match"].get("homeTeam", {}).get("name", "")
                        away_team = app["match"].get("awayTeam", {}).get("name", "")
                        comp_name = app["match"].get("competition", {}).get("name", "")

                        db_game_id = find_matching_game(
                            app_moment=syd_dt,
                            app_home_team=home_team,
                            app_away_team=away_team,
                            db_games=db_games,
                            app_competition_name=comp_name,
                        )
                        if db_game_id:
                            app["db_game_id"] = db_game_id

                        # Clean up temp key
                        if "sydney_moment" in app["match"]:
                            del app["match"]["sydney_moment"]

            return appointments

        except httpx.RequestError as exc:
            logger.error(f"RX API error fetching appointments: {exc}")
            raise HTTPException(
                status_code=503, detail="RugbyXplorer service unavailable"
            )


@router.get("/profile")
async def get_profile(userId: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ")[1]
    headers = get_rx_headers(token)

    url = f"{RX_BASE_URL}/rau/api/v2/myprofile/{userId}"

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif res.status_code != 200:
                raise HTTPException(
                    status_code=res.status_code, detail="Failed to fetch profile"
                )
            return res.json()
        except httpx.RequestError as exc:
            logger.error(f"RX API error fetching profile: {exc}")
            raise HTTPException(
                status_code=503, detail="RugbyXplorer service unavailable"
            )
