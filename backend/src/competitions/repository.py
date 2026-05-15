"""Competition data access layer."""

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.competitions.models import Competition, Round, CompetitionMapping
from src.clubs.models import Team
from src.games.models import Game


async def get_all_competitions(db: AsyncSession) -> list[dict]:
    """Fetch all competitions with team and round counts."""
    stmt = (
        select(
            Competition.id,
            Competition.name,
            Competition.external_id,
            Competition.competition_mapping_id,
            CompetitionMapping.parent_competition,
            CompetitionMapping.division,
            CompetitionMapping.grade,
            func.count(func.distinct(Team.id)).label("team_count"),
            func.count(func.distinct(Round.id)).label("round_count"),
        )
        .outerjoin(Team, Team.competition_id == Competition.id)
        .outerjoin(Round, Round.competition_id == Competition.id)
        .outerjoin(CompetitionMapping, Competition.competition_mapping_id == CompetitionMapping.id)
        .group_by(
            Competition.id, Competition.name, Competition.external_id, 
            Competition.competition_mapping_id,
            CompetitionMapping.parent_competition,
            CompetitionMapping.division,
            CompetitionMapping.grade
        )
        .order_by(Competition.name)
    )
    result = await db.execute(stmt)
    return [row._asdict() for row in result.all()]


async def get_competition_by_id(db: AsyncSession, competition_id: int) -> dict | None:
    """Fetch a single competition with its rounds and game counts."""
    # Get competition
    stmt = select(Competition).where(Competition.id == competition_id)
    result = await db.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        return None

    # Get rounds with game counts
    rounds_stmt = (
        select(
            Round.id,
            Round.name,
            Round.number,
            Round.external_id,
            func.count(Game.id).label("game_count"),
            func.sum(
                case((Game.status == "completed", 1), else_=0)
            ).label("completed_game_count"),
            func.max(Game.game_date).label("latest_game_date"),
        )
        .outerjoin(Game, Game.round_id == Round.id)
        .where(Round.competition_id == competition_id)
        .group_by(Round.id)
        .order_by(Round.number.nulls_last(), Round.id)
    )
    rounds_result = await db.execute(rounds_stmt)
    rounds = [row._asdict() for row in rounds_result.all()]

    # Get team count
    team_stmt = select(func.count(Team.id)).where(Team.competition_id == competition_id)
    team_count = (await db.execute(team_stmt)).scalar()

    return {
        "id": comp.id,
        "name": comp.name,
        "external_id": comp.external_id,
        "rounds": rounds,
        "team_count": team_count,
    }
