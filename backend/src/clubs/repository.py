"""Club data access layer."""

from sqlalchemy import select, func, case, and_, or_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from src.clubs.models import Club, Team
from src.competitions.models import Competition, CompetitionMapping
from src.games.models import Game


async def get_all_clubs(db: AsyncSession) -> list[dict]:
    """Fetch all clubs with team counts and season win/loss/draw record."""
    record_sub = (
        select(
            Team.club_id,
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score > Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score > Game.home_score), 1),
                else_=0
            )).label("wins"),
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score < Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score < Game.home_score), 1),
                else_=0
            )).label("losses"),
            func.sum(case(
                (Game.home_score == Game.away_score, 1),
                else_=0
            )).label("draws"),
        )
        .join(
            Game,
            and_(
                or_(Game.home_team_id == Team.id, Game.away_team_id == Team.id),
                Game.status == "completed",
            ),
        )
        .group_by(Team.club_id)
        .subquery("record_sub")
    )

    stmt = (
        select(
            Club.id,
            Club.name,
            Club.short_name,
            Club.logo_url,
            func.count(Team.id).label("team_count"),
            func.coalesce(record_sub.c.wins, 0).label("wins"),
            func.coalesce(record_sub.c.losses, 0).label("losses"),
            func.coalesce(record_sub.c.draws, 0).label("draws"),
            CompetitionMapping.id.label("mapping_id"),
            CompetitionMapping.parent_competition,
            CompetitionMapping.name.label("mapping_name"),
            CompetitionMapping.division,
            CompetitionMapping.grade,
        )
        .outerjoin(Team, Team.club_id == Club.id)
        .outerjoin(record_sub, record_sub.c.club_id == Club.id)
        .outerjoin(CompetitionMapping, Club.competition_mapping_id == CompetitionMapping.id)
        .group_by(
            Club.id, Club.name, Club.short_name, Club.logo_url,
            record_sub.c.wins, record_sub.c.losses, record_sub.c.draws,
            CompetitionMapping.id, CompetitionMapping.parent_competition,
            CompetitionMapping.name, CompetitionMapping.division, CompetitionMapping.grade,
        )
        .order_by(CompetitionMapping.parent_competition, CompetitionMapping.division, Club.name)
    )
    result = await db.execute(stmt)
    
    clubs = []
    for row in result.all():
        d = row._asdict()
        # Nest competition_mapping
        if d.get("mapping_id"):
            d["competition_mapping"] = {
                "id": d.pop("mapping_id"),
                "parent_competition": d.pop("parent_competition"),
                "name": d.pop("mapping_name"),
                "division": d.pop("division"),
                "grade": d.pop("grade"),
            }
        else:
            d["competition_mapping"] = None
            # Cleanup unwanted mapping fields if they are None
            for k in ["mapping_id", "parent_competition", "mapping_name", "division", "grade"]:
                if k in d: d.pop(k)
        clubs.append(d)
        
    return clubs


async def get_club_by_id(db: AsyncSession, club_id: int) -> dict | None:
    """Fetch a single club with its teams and competition names."""
    stmt = (
        select(
            Club.id,
            Club.name,
            Club.short_name,
            Club.logo_url,
            CompetitionMapping.id.label("mapping_id"),
            CompetitionMapping.parent_competition,
            CompetitionMapping.name.label("mapping_name"),
            CompetitionMapping.division,
            CompetitionMapping.grade,
        )
        .outerjoin(CompetitionMapping, Club.competition_mapping_id == CompetitionMapping.id)
        .where(Club.id == club_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    d = row._asdict()
    
    # Nest competition_mapping
    if d.get("mapping_id"):
        d["competition_mapping"] = {
            "id": d.pop("mapping_id"),
            "parent_competition": d.pop("parent_competition"),
            "name": d.pop("mapping_name"),
            "division": d.pop("division"),
            "grade": d.pop("grade"),
        }
    else:
        d["competition_mapping"] = None
        for k in ["mapping_id", "parent_competition", "mapping_name", "division", "grade"]:
            if k in d: d.pop(k)

    # Get teams with competition names
    teams_stmt = (
        select(
            Team.id,
            Team.name,
            Team.external_id,
            Competition.name.label("competition_name"),
        )
        .join(Competition, Competition.id == Team.competition_id)
        .where(Team.club_id == club_id)
        .order_by(Competition.name)
    )
    teams_result = await db.execute(teams_stmt)
    teams = [row._asdict() for row in teams_result.all()]
    d["teams"] = teams

    return d
