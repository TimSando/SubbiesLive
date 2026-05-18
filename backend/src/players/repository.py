"""Player data access layer."""

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.players.models import Player
from src.clubs.models import Club, Team
from src.competitions.models import Competition
from src.games.models import GameEvent, Game, PlayerHistory


async def get_players(
    db: AsyncSession,
    search: str | None = None,
    team_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch players with optional search and team filter."""
    stmt = (
        select(
            Player.id,
            Player.name,
            Player.external_id,
            Player.thumbnail_url,
        )
    )

    if search:
        stmt = stmt.where(Player.name.ilike(f"%{search}%"))

    if team_id:
        stmt = stmt.join(
            PlayerHistory, PlayerHistory.player_id == Player.id
        ).where(PlayerHistory.team_id == team_id).distinct()

    stmt = stmt.order_by(Player.name).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [row._asdict() for row in result.all()]


async def get_player_by_id(db: AsyncSession, player_id: int) -> dict | None:
    """Fetch a single player with team history and aggregated stats."""
    # Get player
    stmt = select(Player).where(Player.id == player_id)
    result = await db.execute(stmt)
    player = result.scalar_one_or_none()
    if not player:
        return None

    # Get team associations
    teams_stmt = (
        select(
            Team.id.label("team_id"),
            Team.name.label("team_name"),
            Club.name.label("club_name"),
            Competition.name.label("competition_name"),
        )
        .select_from(PlayerHistory)
        .join(Team, Team.id == PlayerHistory.team_id)
        .join(Club, Club.id == Team.club_id)
        .join(Competition, Competition.id == Team.competition_id)
        .where(PlayerHistory.player_id == player_id)
        .group_by(Team.id, Team.name, Club.name, Competition.name)
        .order_by(Competition.name)
    )
    teams_result = await db.execute(teams_stmt)
    teams = [row._asdict() for row in teams_result.all()]

    # Get aggregated stats from player history
    stats_stmt = (
        select(
            func.sum(PlayerHistory.tries).label("tries"),
            func.sum(PlayerHistory.conversions).label("conversions"),
            func.sum(PlayerHistory.penalty_goals).label("penalty_goals"),
            func.sum(PlayerHistory.drop_goals).label("drop_goals"),
            func.sum(PlayerHistory.yellow_cards).label("yellow_cards"),
            func.sum(PlayerHistory.red_cards).label("red_cards"),
            func.sum(PlayerHistory.points).label("points"),
            func.count(PlayerHistory.game_id).label("games_played"),
        )
        .where(PlayerHistory.player_id == player_id)
    )
    stats_result = await db.execute(stats_stmt)
    row = stats_result.one_or_none()

    stats = {
        "total_tries": 0,
        "total_conversions": 0,
        "total_penalty_goals": 0,
        "total_drop_goals": 0,
        "total_yellow_cards": 0,
        "total_red_cards": 0,
        "total_points": 0,
        "games_played": 0,
    }

    if row:
        stats["total_tries"] = int(row.tries or 0)
        stats["total_conversions"] = int(row.conversions or 0)
        stats["total_penalty_goals"] = int(row.penalty_goals or 0)
        stats["total_drop_goals"] = int(row.drop_goals or 0)
        stats["total_yellow_cards"] = int(row.yellow_cards or 0)
        stats["total_red_cards"] = int(row.red_cards or 0)
        stats["total_points"] = int(row.points or 0)
        stats["games_played"] = int(row.games_played or 0)


    # Get most recent club name
    recent_club_stmt = (
        select(Club.name)
        .select_from(PlayerHistory)
        .join(Team, Team.id == PlayerHistory.team_id)
        .join(Club, Club.id == Team.club_id)
        .join(Game, Game.id == PlayerHistory.game_id)
        .where(PlayerHistory.player_id == player_id)
        .order_by(desc(Game.game_date))
        .limit(1)
    )
    recent_club = (await db.execute(recent_club_stmt)).scalar_one_or_none()
    
    if not recent_club and teams:
        recent_club = teams[0]["club_name"]

    return {
        "id": player.id,
        "name": player.name,
        "dob": player.dob,
        "image_url": player.image_url,
        "thumbnail_url": player.thumbnail_url,
        "external_id": player.external_id,
        "teams": teams,
        "stats": stats,
        "recent_club": recent_club,
    }
