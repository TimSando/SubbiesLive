from datetime import datetime
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.core.cache import ttl_cache
from src.ratings.models import TeamRatingHistory, GameSquad, PlayerImpactScore
from src.players.models import Player
from src.ratings.elo import predict_match, BASE_RATING, HOME_ADVANTAGE_OFFSET
from src.ratings.schemas import (
    PredictionResponse,
    PlayerInsight,
    TeamPlayerInsights,
    PlayerImpactResponse,
    PlayerImpactEntry,
)
from src.games import repository as games_repo


async def get_current_rating(db: AsyncSession, team_id: int) -> float:
    """Fetch the most recent rating_after for a team, defaulting to BASE_RATING."""
    stmt = (
        select(TeamRatingHistory.rating_after)
        .where(TeamRatingHistory.team_id == team_id)
        .order_by(desc(TeamRatingHistory.created_at), desc(TeamRatingHistory.id))
        .limit(1)
    )
    result = await db.execute(stmt)
    rating = result.scalar_one_or_none()
    return rating if rating is not None else BASE_RATING


async def get_current_ratings_bulk(
    db: AsyncSession, team_ids: list[int]
) -> dict[int, float]:
    """Fetch current ratings for a list of team IDs in a single query."""
    if not team_ids:
        return {}

    stmt = (
        select(TeamRatingHistory.team_id, TeamRatingHistory.rating_after)
        .where(TeamRatingHistory.team_id.in_(team_ids))
        .distinct(TeamRatingHistory.team_id)
        .order_by(
            TeamRatingHistory.team_id,
            desc(TeamRatingHistory.created_at),
            desc(TeamRatingHistory.id),
        )
    )
    result = await db.execute(stmt)
    ratings = {row.team_id: row.rating_after for row in result.all()}

    # Backfill default rating for any teams that don't have history yet
    for tid in team_ids:
        if tid not in ratings:
            ratings[tid] = BASE_RATING
    return ratings


async def get_rating_history(
    db: AsyncSession, team_id: int, limit: int = 20
) -> list[TeamRatingHistory]:
    """Fetch the rating history for a team, sorted from newest to oldest."""
    stmt = (
        select(TeamRatingHistory)
        .where(TeamRatingHistory.team_id == team_id)
        .order_by(desc(TeamRatingHistory.created_at), desc(TeamRatingHistory.id))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_team_baseline_and_scores(db: AsyncSession, team_id: int) -> tuple[float, dict[int, float]]:
    """Helper to calculate full strength baseline and return career scores map."""
    stmt = (
        select(PlayerImpactScore.player_id, PlayerImpactScore.impact_score)
        .where(PlayerImpactScore.team_id == team_id)
        .where(PlayerImpactScore.year.is_(None))
        .order_by(desc(PlayerImpactScore.impact_score))
    )
    res = await db.execute(stmt)
    rows = res.all()
    
    scores_map = {row.player_id: row.impact_score for row in rows}
    
    # Baseline is sum of top-15 career impact scores
    top_15_scores = [row.impact_score for row in rows[:15]]
    baseline = sum(top_15_scores) if top_15_scores else 0.0
    return baseline, scores_map


async def _get_player_insight(db: AsyncSession, team_id: int, player_id: int, player_name: str, career_score: float, current_year: int) -> PlayerInsight:
    """Fetch seasonal stats and history details for a key player."""
    # 1. Get season impact score
    stmt_season = (
        select(PlayerImpactScore.impact_score)
        .where(PlayerImpactScore.player_id == player_id)
        .where(PlayerImpactScore.team_id == team_id)
        .where(PlayerImpactScore.year == current_year)
    )
    res_season = await db.execute(stmt_season)
    season_score = res_season.scalar_one_or_none()

    # 2. Get games this season and last played game
    stmt_games = (
        select(text("COUNT(ph.id) as cnt"))
        .select_from(text("player_history ph"))
        .join(text("games g"), text("ph.game_id = g.id"))
        .where(text("ph.player_id = :pid AND ph.team_id = :tid AND g.status = 'completed' AND EXTRACT(YEAR FROM g.game_date) = :year"))
    )
    res_games = await db.execute(stmt_games, {"pid": player_id, "tid": team_id, "year": current_year})
    games_this_season = res_games.scalar() or 0

    # 3. Get last played game info
    stmt_last = (
        select(text("g.game_date, r.name as round_name"))
        .select_from(text("player_history ph"))
        .join(text("games g"), text("ph.game_id = g.id"))
        .join(text("rounds r"), text("g.round_id = r.id"))
        .where(text("ph.player_id = :pid AND ph.team_id = :tid AND g.status = 'completed'"))
        .order_by(text("g.game_date DESC"))
        .limit(1)
    )
    res_last = await db.execute(stmt_last, {"pid": player_id, "tid": team_id})
    last_row = res_last.first()

    last_played_round = None
    weeks_since_last_game = None

    if last_row:
        game_date, round_name = last_row
        last_played_round = round_name
        
        # Parse game_date to datetime if it's a string, or check type
        if isinstance(game_date, str):
            dt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
        else:
            dt = game_date
        
        diff = datetime.now() - dt.replace(tzinfo=None)
        weeks_since_last_game = max(0, int(diff.days / 7))

    return PlayerInsight(
        player_id=player_id,
        player_name=player_name,
        impact_score=career_score,
        impact_score_season=season_score,
        confidence="high" if games_this_season >= 15 else ("medium" if games_this_season >= 8 else "low"),
        games_this_season=games_this_season,
        last_played_round=last_played_round,
        weeks_since_last_game=weeks_since_last_game,
    )


async def _get_team_player_insights(db: AsyncSession, team_id: int, squad_players: list[int] | None, current_year: int) -> TeamPlayerInsights:
    """Collect key players and compute squad modifier."""
    baseline, career_scores = await _get_team_baseline_and_scores(db, team_id)

    # Fetch top 3 key players by career impact score
    stmt_keys = (
        select(PlayerImpactScore.player_id, Player.name, PlayerImpactScore.impact_score)
        .join(Player, PlayerImpactScore.player_id == Player.id)
        .where(PlayerImpactScore.team_id == team_id)
        .where(PlayerImpactScore.year.is_(None))
        .order_by(desc(PlayerImpactScore.impact_score))
        .limit(3)
    )
    res_keys = await db.execute(stmt_keys)
    key_rows = res_keys.all()

    key_players = []
    for row in key_rows:
        pid, pname, score = row
        insight = await _get_player_insight(db, team_id, pid, pname, score, current_year)
        key_players.append(insight)

    # Compute squad modifier
    squad_modifier = None
    squad_modifier_source = "no_squad_data"

    if squad_players:
        squad_impact = sum(career_scores.get(pid, 0.0) for pid in squad_players)
        squad_modifier = squad_impact - baseline
        squad_modifier_source = "game_squads"

    return TeamPlayerInsights(
        key_players=key_players,
        squad_modifier=squad_modifier,
        squad_modifier_source=squad_modifier_source,
    )


@ttl_cache(ttl_seconds=300)
async def get_prediction_for_game(
    db: AsyncSession, game_id: int
) -> PredictionResponse | None:
    """Look up teams, fetch their current ratings, run prediction, and return PredictionResponse."""
    game = await games_repo.get_game_by_id(db, game_id)
    if not game:
        return None

    home_team_id = game["home_team"]["id"]
    away_team_id = game["away_team"]["id"]

    home_rating = await get_current_rating(db, home_team_id)
    away_rating = await get_current_rating(db, away_team_id)

    # Fetch named squads for the game
    stmt_squad = (
        select(GameSquad.player_id, GameSquad.team_id)
        .where(GameSquad.game_id == game_id)
    )
    res_squad = await db.execute(stmt_squad)
    squad_rows = res_squad.all()

    home_squad = [row.player_id for row in squad_rows if row.team_id == home_team_id]
    away_squad = [row.player_id for row in squad_rows if row.team_id == away_team_id]

    current_year = datetime.now().year # Fallback or configuration

    home_insights = await _get_team_player_insights(db, home_team_id, home_squad if home_squad else None, current_year)
    away_insights = await _get_team_player_insights(db, away_team_id, away_squad if away_squad else None, current_year)

    home_modifier = home_insights.squad_modifier or 0.0
    away_modifier = away_insights.squad_modifier or 0.0

    # Calculate effective ratings
    home_eff = home_rating + home_modifier
    away_eff = away_rating + away_modifier

    pred = predict_match(home_eff, away_eff)

    has_history = home_rating != BASE_RATING or away_rating != BASE_RATING

    return PredictionResponse(
        game_id=game_id,
        home_win_probability=pred["home_prob"],
        away_win_probability=pred["away_prob"],
        draw_probability=pred["draw_prob"],
        home_odds_display=pred["home_odds_display"],
        away_odds_display=pred["away_odds_display"],
        confidence="high" if has_history else "low",
        rating_diff=home_rating - away_rating,
        player_insights={
            "home_team": home_insights,
            "away_team": away_insights,
        }
    )


async def get_team_impact_rankings(db: AsyncSession, team_id: int, year: int | None = None) -> PlayerImpactResponse | None:
    """Fetch player impact scores for a team, sorted by impact_score descending."""
    # Verify team exists
    team_check = await db.execute(
        select(text("name")).select_from(text("teams")).where(text("id = :tid")),
        {"tid": team_id}
    )
    team_name = team_check.scalar()
    if not team_name:
        return None

    # Fetch available years
    stmt_years = (
        select(PlayerImpactScore.year)
        .where(PlayerImpactScore.team_id == team_id)
        .where(PlayerImpactScore.year.isnot(None))
        .distinct()
    )
    res_years = await db.execute(stmt_years)
    available_years = sorted([row.year for row in res_years.all()])

    # Fetch rankings
    stmt = (
        select(
            PlayerImpactScore.player_id,
            Player.name.label("player_name"),
            PlayerImpactScore.impact_score,
            PlayerImpactScore.games_with,
            PlayerImpactScore.games_without,
            PlayerImpactScore.win_rate_with,
            PlayerImpactScore.win_rate_without,
            PlayerImpactScore.confidence
        )
        .join(Player, PlayerImpactScore.player_id == Player.id)
        .where(PlayerImpactScore.team_id == team_id)
        .order_by(desc(PlayerImpactScore.impact_score))
    )

    if year is not None:
        stmt = stmt.where(PlayerImpactScore.year == year)
    else:
        stmt = stmt.where(PlayerImpactScore.year.is_(None))

    res = await db.execute(stmt)
    rows = res.all()

    players = []
    for r in rows:
        # Get career score helper for entries
        stmt_career = (
            select(PlayerImpactScore.impact_score)
            .where(PlayerImpactScore.player_id == r.player_id)
            .where(PlayerImpactScore.team_id == team_id)
            .where(PlayerImpactScore.year.is_(None))
        )
        res_career = await db.execute(stmt_career)
        career_score = res_career.scalar_one_or_none() or r.impact_score

        players.append(
            PlayerImpactEntry(
                player_id=r.player_id,
                player_name=r.player_name,
                impact_score=r.impact_score,
                impact_score_career=career_score,
                confidence=r.confidence,
                games_with=r.games_with,
                games_without=r.games_without,
                win_rate_with=r.win_rate_with,
                win_rate_without=r.win_rate_without,
            )
        )

    # Compute baseline
    baseline, _ = await _get_team_baseline_and_scores(db, team_id)

    return PlayerImpactResponse(
        team_id=team_id,
        team_name=team_name,
        year=year,
        full_strength_baseline=baseline,
        players=players,
        available_years=available_years,
    )
