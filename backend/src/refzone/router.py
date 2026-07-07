import logging
import re
import base64
import json
import time
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel
import httpx
from src.core.config import get_settings

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

# In-memory cache for profiles to avoid downstream failures
_cached_profiles: Dict[str, dict] = {}


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class Verify2FARequest(BaseModel):
    code: str
    token: str
    remember_me: bool = False


def decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        # Pad payload if necessary
        padding = len(payload_b64) % 4
        if padding:
            payload_b64 += "=" * (4 - padding)
        decoded = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"Failed to decode JWT payload: {e}")
        return {}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    settings = get_settings()
    secure = settings.cookie_secure
    samesite = "lax" if not secure else "strict"

    # Calculate dynamic max_age for access token based on its expiration
    access_max_age = 3600  # fallback: 1 hour
    access_payload = decode_jwt_payload(access_token)
    access_exp = access_payload.get("exp")
    if access_exp:
        access_max_age = max(0, int(access_exp - time.time()))

    # Set rx_access_token
    response.set_cookie(
        key="rx_access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api/refzone",
        max_age=access_max_age,
    )

    # Calculate dynamic max_age for refresh token based on its expiration
    refresh_max_age = 7 * 24 * 3600
    refresh_payload = decode_jwt_payload(refresh_token)
    refresh_exp = refresh_payload.get("exp")
    if refresh_exp:
        refresh_max_age = max(0, int(refresh_exp - time.time()))

    # Set rx_refresh_token
    response.set_cookie(
        key="rx_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api/refzone",
        max_age=refresh_max_age,
    )


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


async def perform_login(body: LoginRequest) -> dict:
    global _cached_basic_token
    url = f"{RX_BASE_URL}/rau/api/v3/login"
    payload = {
        "email": body.email,
        "encodedParams": ["email", "password"],
        "password": body.password,
        "samlRequest": {},
    }
    if body.remember_me:
        payload["rememberMe"] = True
        payload["expirationInMinutes"] = 43200

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


@router.post("/login")
async def rx_login(body: LoginRequest, response: Response):
    rx_data = await perform_login(body)

    # Check for MFA challenge
    if rx_data.get("isMfaEnabled") is True:
        return {"status": "mfa_required", "mfa_token": rx_data.get("token")}

    if "jwtTokens" in rx_data and "accessToken" in rx_data["jwtTokens"]:
        jwt_tokens = rx_data["jwtTokens"]
        access_token = jwt_tokens.get("accessToken")
        refresh_token = jwt_tokens.get("refreshToken")
        set_auth_cookies(response, access_token, refresh_token)
        user_id = rx_data.get("userId")
        if user_id and "profile" in rx_data:
            _cached_profiles[str(user_id)] = rx_data["profile"]
        return {"status": "ok", "userId": user_id}

    return rx_data


@router.post("/verify-2fa")
async def verify_2fa(body: Verify2FARequest, response: Response):
    url = f"{RX_BASE_URL}/rau/api/v1/mfa-verify"
    raw_auth = f"{body.token}:{body.code}"
    basic_val = base64.b64encode(raw_auth.encode("utf-8")).decode("utf-8")

    headers = {
        "clientId": "portal",
        "Content-Type": "application/json",
        "Origin": "https://auth.rugbyxplorer.com.au",
        "Referer": "https://auth.rugbyxplorer.com.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
        "Authorization": f"Basic {basic_val}",
    }

    payload = {}
    if body.remember_me:
        payload["rememberMe"] = True
        payload["expirationInMinutes"] = 43200

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if r.status_code != 200:
                logger.error(
                    f"RX MFA verify failed: status={r.status_code}, response={r.text}"
                )
                raise HTTPException(
                    status_code=r.status_code,
                    detail=f"MFA verification failed: {r.text}",
                )

            rx_data = r.json()
            logger.info(f"verify_2fa response from RX: {rx_data}")
            if "jwtTokens" in rx_data and "accessToken" in rx_data["jwtTokens"]:
                jwt_tokens = rx_data["jwtTokens"]
                access_token = jwt_tokens.get("accessToken")
                refresh_token = jwt_tokens.get("refreshToken")
                set_auth_cookies(response, access_token, refresh_token)

                user_id = rx_data.get("userId")
                if user_id and "profile" in rx_data:
                    _cached_profiles[str(user_id)] = rx_data["profile"]

                # Strip jwtTokens block and return other fields like userId
                out_data = {k: v for k, v in rx_data.items() if k != "jwtTokens"}
                return out_data

            raise HTTPException(
                status_code=500,
                detail="MFA verification succeeded but no tokens returned",
            )
        except httpx.RequestError as exc:
            logger.error(f"RX API error verifying 2FA: {exc}")
            raise HTTPException(
                status_code=503, detail="RugbyXplorer service unavailable"
            )


@router.get("/status")
async def get_status(request: Request, response: Response):
    token = request.cookies.get("rx_access_token")
    refresh_token = request.cookies.get("rx_refresh_token")

    if not token:
        # Try silently refreshing using refresh token as fallback bearer
        if refresh_token:
            logger.info(
                "Access token missing in get_status. Attempting silent refresh..."
            )
            try:
                rx_data = await perform_refresh(refresh_token)
                if "jwtTokens" in rx_data and "accessToken" in rx_data["jwtTokens"]:
                    jwt_tokens = rx_data["jwtTokens"]
                    access_token = jwt_tokens.get("accessToken")
                    new_refresh_token = jwt_tokens.get("refreshToken") or refresh_token
                    set_auth_cookies(response, access_token, new_refresh_token)
                    token = access_token
                    logger.info("Silent refresh in get_status succeeded.")
            except Exception as e:
                logger.error(f"Silent refresh in get_status failed: {e}")

    if not token:
        return {"authenticated": False, "userId": None}

    payload = decode_jwt_payload(token)
    user_id = payload.get("userId") or payload.get("sub")
    if not user_id:
        return {"authenticated": False, "userId": None}

    exp = payload.get("exp")
    if exp and time.time() > exp:
        # Access token is expired — use it to attempt refresh (RX may still accept it)
        # Fall back to refresh token if access token is rejected
        if refresh_token:
            logger.info(
                "Access token expired in get_status. Attempting silent refresh..."
            )
            try:
                rx_data = await perform_refresh(token)
                if "jwtTokens" in rx_data and "accessToken" in rx_data["jwtTokens"]:
                    jwt_tokens = rx_data["jwtTokens"]
                    access_token = jwt_tokens.get("accessToken")
                    new_refresh_token = jwt_tokens.get("refreshToken") or refresh_token
                    set_auth_cookies(response, access_token, new_refresh_token)
                    payload = decode_jwt_payload(access_token)
                    user_id = payload.get("userId") or payload.get("sub")
                    logger.info("Silent refresh in get_status succeeded.")
                else:
                    return {"authenticated": False, "userId": None}
            except Exception as e:
                logger.error(f"Silent refresh in get_status failed: {e}")
                return {"authenticated": False, "userId": None}
        else:
            return {"authenticated": False, "userId": None}

    return {"authenticated": True, "userId": str(user_id)}


async def perform_refresh(bearer_token: str) -> dict:
    """Refresh RX session using the v1 refreshToken endpoint.

    The RugbyXplorer v1 endpoint expects a GET request with the current
    JWT (access or refresh token) as a Bearer token in the Authorization header.

    When the token is still valid, RX may return 200 with an empty body,
    meaning "no refresh needed". In that case we return the existing token.
    """
    url = f"{RX_AUTH_PAGE}/rau/api/v1/auth/refreshToken/"
    headers = get_rx_headers(bearer_token)

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, timeout=10.0)
            if r.status_code != 200:
                logger.error(
                    f"RX token refresh failed: status={r.status_code}, response={r.text}"
                )
                raise HTTPException(
                    status_code=r.status_code, detail="Token refresh failed"
                )

            raw_text = r.text.strip()
            logger.info(
                f"RX token refresh 200. Body length={len(raw_text)}, preview={raw_text[:200] if raw_text else '(empty)'}"
            )

            # RX returns empty body when the current token is still valid
            if not raw_text:
                logger.info(
                    "RX returned empty body — token still valid, no rotation needed."
                )
                return {
                    "jwtTokens": {"accessToken": bearer_token},
                    "tokenStillValid": True,
                }

            try:
                data = r.json()
            except Exception as json_err:
                logger.error(
                    f"RX refresh response is not valid JSON: {json_err}, body={raw_text[:500]}"
                )
                raise HTTPException(
                    status_code=502,
                    detail="Invalid response from RugbyXplorer refresh",
                )

            logger.info(
                f"RX token refresh succeeded. Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            )
            # Normalize: RX v1 may return 'token' instead of 'accessToken' inside jwtTokens
            if isinstance(data, dict) and "jwtTokens" in data:
                jwt = data["jwtTokens"]
                if "token" in jwt and "accessToken" not in jwt:
                    jwt["accessToken"] = jwt["token"]
            return data
        except httpx.RequestError as exc:
            logger.error(f"RX API error refreshing token: {exc}")
            raise HTTPException(
                status_code=503, detail="RugbyXplorer service unavailable"
            )


@router.post("/refresh")
async def rx_refresh(request: Request, response: Response):
    # Prefer access token as bearer (what RX expects), fall back to refresh token
    access_token = request.cookies.get("rx_access_token")
    refresh_token = request.cookies.get("rx_refresh_token")
    bearer_token = access_token or refresh_token
    if not bearer_token:
        raise HTTPException(status_code=401, detail="Missing auth cookies")

    rx_data = await perform_refresh(bearer_token)
    if "jwtTokens" in rx_data and "accessToken" in rx_data["jwtTokens"]:
        jwt_tokens = rx_data["jwtTokens"]
        new_access_token = jwt_tokens.get("accessToken")
        new_refresh_token = jwt_tokens.get("refreshToken") or refresh_token
        set_auth_cookies(response, new_access_token, new_refresh_token)
        return {"status": "ok"}

    raise HTTPException(status_code=500, detail="Tokens missing in refresh response")


@router.post("/logout")
async def rx_logout(request: Request, response: Response):
    token = request.cookies.get("rx_access_token")
    if token:
        payload = decode_jwt_payload(token)
        user_id = payload.get("userId") or payload.get("sub")
        if user_id:
            _cached_profiles.pop(str(user_id), None)

    response.delete_cookie(key="rx_access_token", path="/api/refzone")
    response.delete_cookie(key="rx_refresh_token", path="/api/refzone")
    return {"status": "logged_out"}


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
async def get_appointments(userId: str, db: DbSession, request: Request):
    token = request.cookies.get("rx_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing rx_access_token cookie")

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

            # Combine appointments and deduplicate by _id
            seen_ids = set()
            appointments = []
            if isinstance(confirmed_data, list):
                for app in confirmed_data:
                    app_id = app.get("_id")
                    if app_id:
                        seen_ids.add(app_id)
                    appointments.append(app)

            if isinstance(pending_data, list):
                for app in pending_data:
                    app_id = app.get("_id")
                    if app_id and app_id in seen_ids:
                        continue
                    # Make sure status is set/normalized
                    if "status" not in app:
                        app["status"] = "pending"
                    if app_id:
                        seen_ids.add(app_id)
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
async def get_profile(userId: str, request: Request):
    token = request.cookies.get("rx_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing rx_access_token cookie")

    if userId in _cached_profiles:
        logger.info(f"Serving profile for {userId} from memory cache")
        return _cached_profiles[userId]

    headers = get_rx_headers(token)

    url = f"{RX_BASE_URL}/rau/api/v2/myprofile/{userId}"

    async with httpx.AsyncClient() as client:
        try:
            res = await client.request(
                "GET", url, headers=headers, json={"userID": userId}, timeout=10.0
            )
            logger.info(f"myprofile req headers: {res.request.headers}")
            logger.info(f"myprofile req content: {res.request.read()}")
            logger.info(f"myprofile res status: {res.status_code}")
            logger.info(f"myprofile res body: {res.text}")
            if res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif res.status_code != 200:
                logger.warning(
                    f"Failed to fetch profile for {userId} from RugbyXplorer (status={res.status_code}). Using fallback profile."
                )
                return {"firstname": "Referee", "lastname": "", "headshot": ""}

            profile_data = res.json()
            if isinstance(profile_data, dict):
                _cached_profiles[userId] = profile_data
            return profile_data
        except httpx.RequestError as exc:
            logger.error(f"RX API error fetching profile: {exc}")
            logger.warning(
                f"Error fetching profile from RugbyXplorer: {exc}. Using fallback profile."
            )
            return {"firstname": "Referee", "lastname": "", "headshot": ""}
