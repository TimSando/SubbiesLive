"""Clubs API router."""

import logging
import os
import urllib.parse
import httpx

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from src.core.dependencies import DbSession
from src.clubs import service
from src.clubs.schemas import ClubBrief, ClubDetail
from src.clubs.models import Club

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Define cache directory relative to the backend source root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(base_dir, "logos_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


@router.get("", response_model=list[ClubBrief])
async def list_clubs(db: DbSession, year: int | None = Query(None)):
    """List all clubs with team counts."""
    return await service.list_clubs(db, year)


@router.get("/{club_id}", response_model=ClubDetail)
async def get_club(club_id: int, db: DbSession, year: int | None = Query(None)):
    """Get a single club with its teams across competitions."""
    result = await service.get_club(db, club_id, year)
    if not result:
        raise HTTPException(status_code=404, detail="Club not found")
    return result


@router.get("/{club_id}/logo")
async def get_club_logo(club_id: int, db: DbSession):
    """Serve cached club logo, downloading it from remote source on demand if needed."""
    # 1. Look for cached file
    try:
        matched_files = [
            f for f in os.listdir(CACHE_DIR) if f.startswith(f"{club_id}.")
        ]
        if matched_files:
            local_path = os.path.join(CACHE_DIR, matched_files[0])
            return FileResponse(
                local_path,
                headers={"Cache-Control": "public, max-age=31536000, immutable"},
            )
    except Exception as e:
        logger.error(f"Error checking cached logo for club {club_id}: {e}")

    # 2. If not found in cache, query DB for the logo_url
    stmt = select(Club.logo_url).where(Club.id == club_id)
    result = await db.execute(stmt)
    logo_url = result.scalar_one_or_none()

    if not logo_url:
        # No logo URL configured, return 404 so frontend fallback handles it
        raise HTTPException(status_code=404, detail="Club logo not found")

    # 3. Download the logo
    parsed_url = urllib.parse.urlparse(logo_url)
    _, ext = os.path.splitext(parsed_url.path)
    if not ext:
        ext = ".png"
    ext = ext.lower()

    filename = f"{club_id}{ext}"
    local_path = os.path.join(CACHE_DIR, filename)
    temp_path = f"{local_path}.tmp"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(logo_url, timeout=10.0)
            if response.status_code == 200:
                if len(response.content) < 10 * 1024 * 1024:
                    with open(temp_path, "wb") as f:
                        f.write(response.content)
                    os.replace(temp_path, local_path)
                    return FileResponse(
                        local_path,
                        headers={
                            "Cache-Control": "public, max-age=31536000, immutable"
                        },
                    )
                else:
                    logger.warning(
                        f"Logo file too large for club {club_id}: {len(response.content)} bytes"
                    )
            else:
                logger.warning(
                    f"Failed to download logo for club {club_id} from {logo_url}, status: {response.status_code}"
                )
    except Exception as e:
        logger.error(f"Error downloading logo for club {club_id}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    # Fallback to redirecting to the remote URL directly if we failed to cache it
    return RedirectResponse(url=logo_url)
