from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.core.database import get_db
from src.stats import repository as stats_repo
from src.stats import schemas

router = APIRouter(tags=["stats"])

@router.get("/players", response_model=List[schemas.PlayerStatRow])
async def get_player_leaderboard(
    competition_id: Optional[int] = Query(None),
    parent_competition: Optional[str] = Query(None),
    division: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get player leaderboard stats."""
    return await stats_repo.get_player_stats(db, competition_id, parent_competition, division)

@router.get("/clubs", response_model=List[schemas.ClubStatRow])
async def get_club_leaderboard(
    competition_id: Optional[int] = Query(None),
    parent_competition: Optional[str] = Query(None),
    division: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get club leaderboard stats."""
    return await stats_repo.get_club_stats(db, competition_id, parent_competition, division)

@router.get("/overview", response_model=schemas.SeasonOverview)
async def get_season_overview(
    competition_id: Optional[int] = Query(None),
    parent_competition: Optional[str] = Query(None),
    division: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get high-level season overview stats."""
    return await stats_repo.get_season_overview(db, competition_id, parent_competition, division)

@router.get("/clubs/depth", response_model=List[schemas.ClubDepthRow])
async def get_club_depth_leaderboard(
    competition_id: Optional[int] = Query(None),
    parent_competition: Optional[str] = Query(None),
    division: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get club depth and squad participation stats."""
    return await stats_repo.get_club_depth_stats(db, competition_id, parent_competition, division)

