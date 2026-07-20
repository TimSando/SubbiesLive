"""Database queries for team ratings and predictions."""

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.core.cache import ttl_cache
from src.ratings.models import TeamRatingHistory
from src.ratings.elo import predict_match, BASE_RATING
from src.ratings.schemas import PredictionResponse
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

    pred = predict_match(home_rating, away_rating)

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
    )
