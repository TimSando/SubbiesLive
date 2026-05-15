"""Game data access layer."""

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.games.models import Game, GameEvent
from src.competitions.models import Competition, Round
from src.clubs.models import Club, Team
from src.players.models import Player


HomeTeam = aliased(Team, name="home_team")
AwayTeam = aliased(Team, name="away_team")
HomeClub = aliased(Club, name="home_club")
AwayClub = aliased(Club, name="away_club")


def _build_game_base_query():
    """Build the base SELECT for game queries with team/club/round/competition joins."""
    return (
        select(
            Game.id,
            Game.home_score,
            Game.away_score,
            Game.game_date,
            Game.location,
            Game.status,
            Game.external_id,
            Round.name.label("round_name"),
            Competition.name.label("competition_name"),
            Competition.id.label("competition_id"),
            # Home team
            HomeTeam.id.label("home_team_id"),
            HomeTeam.name.label("home_team_name"),
            HomeClub.name.label("home_club_name"),
            HomeClub.id.label("home_club_id"),
            # Away team
            AwayTeam.id.label("away_team_id"),
            AwayTeam.name.label("away_team_name"),
            AwayClub.name.label("away_club_name"),
            AwayClub.id.label("away_club_id"),
        )
        .join(Round, Round.id == Game.round_id)
        .join(Competition, Competition.id == Round.competition_id)
        .join(HomeTeam, HomeTeam.id == Game.home_team_id)
        .join(AwayTeam, AwayTeam.id == Game.away_team_id)
        .join(HomeClub, HomeClub.id == HomeTeam.club_id)
        .join(AwayClub, AwayClub.id == AwayTeam.club_id)
    )


def _row_to_game_dict(row) -> dict:
    """Convert a query result row to a game dict."""
    data = row._asdict()
    return {
        "id": data["id"],
        "round_name": data["round_name"],
        "competition_name": data["competition_name"],
        "competition_id": data["competition_id"],
        "home_team": {
            "id": data["home_team_id"],
            "name": data["home_team_name"],
            "club_name": data["home_club_name"],
            "club_id": data["home_club_id"],
        },
        "away_team": {
            "id": data["away_team_id"],
            "name": data["away_team_name"],
            "club_name": data["away_club_name"],
            "club_id": data["away_club_id"],
        },
        "home_score": data["home_score"],
        "away_score": data["away_score"],
        "game_date": data["game_date"],
        "location": data["location"],
        "status": data["status"],
        "external_id": data["external_id"],
    }


async def get_games(
    db: AsyncSession,
    competition_id: int | None = None,
    round_id: int | None = None,
    team_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch games with optional filters."""
    stmt = _build_game_base_query()

    if competition_id:
        stmt = stmt.where(Competition.id == competition_id)
    if round_id:
        stmt = stmt.where(Round.id == round_id)
    if team_id:
        stmt = stmt.where((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if status:
        stmt = stmt.where(Game.status == status)

    stmt = stmt.order_by(desc(Game.game_date)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return [_row_to_game_dict(row) for row in result.all()]


async def get_game_by_id(db: AsyncSession, game_id: int) -> dict | None:
    """Fetch a single game with events."""
    stmt = _build_game_base_query().where(Game.id == game_id)
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    game = _row_to_game_dict(row)

    # Fetch events
    events_stmt = (
        select(
            GameEvent.id,
            GameEvent.event_type,
            GameEvent.team_id,
            Team.name.label("team_name"),
            GameEvent.player_id,
            Player.name.label("player_name"),
            GameEvent.player_number,
            GameEvent.points,
            GameEvent.text,
            GameEvent.external_created_at,
        )
        .join(Team, Team.id == GameEvent.team_id)
        .outerjoin(Player, Player.id == GameEvent.player_id)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.external_created_at.asc().nulls_last(), GameEvent.id)
    )
    events_result = await db.execute(events_stmt)
    game["events"] = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "team_id": e.team_id,
            "team_name": e.team_name,
            "player_id": e.player_id,
            "player_name": e.player_name,
            "player_number": e.player_number,
            "points": e.points,
            "text": e.text,
            "external_created_at": e.external_created_at,
        }
        for e in events_result.all()
    ]

    return game


async def get_games_by_competition(db: AsyncSession, competition_id: int) -> list[dict]:
    """Fetch all games for a competition (used by standings calculation)."""
    stmt = (
        select(
            Game.id,
            Game.home_team_id,
            Game.away_team_id,
            Game.home_score,
            Game.away_score,
            Game.status,
        )
        .join(Round, Round.id == Game.round_id)
        .where(Round.competition_id == competition_id)
        .where(Game.status == "completed")
    )
    result = await db.execute(stmt)
    return [row._asdict() for row in result.all()]
