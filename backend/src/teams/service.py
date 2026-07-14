from sqlalchemy.ext.asyncio import AsyncSession
from src.teams import repository


async def get_team_by_id(db: AsyncSession, team_id: int) -> dict | None:
    return await repository.get_team_by_id(db, team_id)

