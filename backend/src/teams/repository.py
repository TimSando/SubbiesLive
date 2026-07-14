from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.clubs.models import Club, Team
from src.competitions.models import Competition
from src.games.models import Game, PlayerHistory


async def get_team_by_id(db: AsyncSession, team_id: int) -> dict | None:
    # 1. Fetch team details
    stmt = (
        select(
            Team.id,
            Team.name,
            Team.external_id,
            Team.club_id,
            Club.name.label("club_name"),
            Club.logo_url.label("club_logo_url"),
            Team.competition_id,
            Competition.name.label("competition_name"),
            Competition.year.label("year"),
        )
        .join(Club, Club.id == Team.club_id)
        .join(Competition, Competition.id == Team.competition_id)
        .where(Team.id == team_id)
    )
    result = await db.execute(stmt)
    team_row = result.first()
    if not team_row:
        return None

    team_data = team_row._asdict()
    year = team_data["year"]

    # 2. Fetch completed games for the team (home or away) to calculate W/D/L and PF/PA
    game_filter = Game.status == "completed"
    if year:
        game_filter = and_(game_filter, func.extract("year", Game.game_date) == year)

    games_stmt = select(
        Game.home_team_id, Game.away_team_id, Game.home_score, Game.away_score
    ).where(
        and_(
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id), game_filter
        )
    )
    games_result = await db.execute(games_stmt)
    games = games_result.all()

    games_played = len(games)
    wins = 0
    losses = 0
    draws = 0
    points_for = 0
    points_against = 0

    for g in games:
        is_home = g.home_team_id == team_id
        our_score = g.home_score if is_home else g.away_score
        opp_score = g.away_score if is_home else g.home_score

        if our_score is not None and opp_score is not None:
            points_for += our_score
            points_against += opp_score
            if our_score > opp_score:
                wins += 1
            elif our_score < opp_score:
                losses += 1
            else:
                draws += 1

    # 3. Fetch player events stats aggregated from PlayerHistory
    history_filter = PlayerHistory.team_id == team_id
    if year:
        history_stmt = (
            select(
                func.sum(PlayerHistory.tries).label("tries"),
                func.sum(PlayerHistory.conversions).label("conversions"),
                func.sum(PlayerHistory.penalty_goals).label("penalty_goals"),
                func.sum(PlayerHistory.drop_goals).label("drop_goals"),
                func.sum(PlayerHistory.yellow_cards).label("yellow_cards"),
                func.sum(PlayerHistory.red_cards).label("red_cards"),
            )
            .join(Game, Game.id == PlayerHistory.game_id)
            .where(
                and_(
                    PlayerHistory.team_id == team_id,
                    func.extract("year", Game.game_date) == year,
                )
            )
        )
    else:
        history_stmt = select(
            func.sum(PlayerHistory.tries).label("tries"),
            func.sum(PlayerHistory.conversions).label("conversions"),
            func.sum(PlayerHistory.penalty_goals).label("penalty_goals"),
            func.sum(PlayerHistory.drop_goals).label("drop_goals"),
            func.sum(PlayerHistory.yellow_cards).label("yellow_cards"),
            func.sum(PlayerHistory.red_cards).label("red_cards"),
        ).where(PlayerHistory.team_id == team_id)

    history_result = await db.execute(history_stmt)
    history_row = history_result.first()

    stats = {
        "games_played": games_played,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "points_for": points_for,
        "points_against": points_against,
        "total_tries": 0,
        "total_conversions": 0,
        "total_penalty_goals": 0,
        "total_drop_goals": 0,
        "total_yellow_cards": 0,
        "total_red_cards": 0,
    }

    if history_row:
        stats["total_tries"] = int(history_row.tries or 0)
        stats["total_conversions"] = int(history_row.conversions or 0)
        stats["total_penalty_goals"] = int(history_row.penalty_goals or 0)
        stats["total_drop_goals"] = int(history_row.drop_goals or 0)
        stats["total_yellow_cards"] = int(history_row.yellow_cards or 0)
        stats["total_red_cards"] = int(history_row.red_cards or 0)

    team_data["stats"] = stats
    return team_data
