"""Clubs API router."""

from fastapi import APIRouter, HTTPException, Query

from src.core.dependencies import DbSession
from src.clubs import service
from src.clubs.schemas import ClubBrief, ClubDetail

router = APIRouter()


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
