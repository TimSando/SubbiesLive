from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.teams import service
from src.teams.schemas import TeamDetail

router = APIRouter()


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await service.get_team_by_id(db, team_id)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result

