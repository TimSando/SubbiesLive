"""Service layer for recalculating and updating team ratings."""

import logging
from sqlalchemy import select, desc, text
from sqlalchemy.orm import Session, joinedload
from src.ratings.elo import (
    BASE_RATING,
    HOME_ADVANTAGE_OFFSET,
    expected_score,
    margin_of_victory_multiplier,
    update_rating,
)
from src.ratings.models import TeamRatingHistory
from src.games.models import Game
from src.competitions.models import Round, Competition

logger = logging.getLogger("ingestion")


def get_effective_rating(
    base_rating: float, is_home: bool, player_modifier: float = 0.0
) -> float:
    """Compute effective rating for a match, applying home advantage and player modifiers."""
    effective = base_rating
    if is_home:
        effective += HOME_ADVANTAGE_OFFSET
    effective += player_modifier
    return effective


def process_completed_game(
    session: Session,
    game: Game,
    franchise_ratings: dict[tuple[int, int], float],
) -> tuple[float, float]:
    """Process a completed game, updates the franchise ratings dict, and writes to history."""
    home_club_id = game.home_team.club_id
    away_club_id = game.away_team.club_id
    comp_mapping_id = game.round.competition.competition_mapping_id or 0

    home_key = (home_club_id, comp_mapping_id)
    away_key = (away_club_id, comp_mapping_id)

    home_rating_before = franchise_ratings.get(home_key, BASE_RATING)
    away_rating_before = franchise_ratings.get(away_key, BASE_RATING)

    home_score = game.home_score if game.home_score is not None else 0
    away_score = game.away_score if game.away_score is not None else 0

    # Calculate effective ratings
    home_eff = get_effective_rating(home_rating_before, is_home=True)
    away_eff = get_effective_rating(away_rating_before, is_home=False)

    # Expected outcomes
    exp_home = expected_score(home_eff, away_eff)
    exp_away = 1.0 - exp_home

    # Actual outcomes
    if home_score > away_score:
        act_home, act_away = 1.0, 0.0
    elif away_score > home_score:
        act_home, act_away = 0.0, 1.0
    else:
        act_home, act_away = 0.5, 0.5

    # MoV multiplier
    score_diff = abs(home_score - away_score)
    mov_mult = margin_of_victory_multiplier(score_diff, home_eff - away_eff)

    # Update ratings
    home_rating_after = update_rating(
        home_rating_before, exp_home, act_home, mov_mult=mov_mult
    )
    away_rating_after = update_rating(
        away_rating_before, exp_away, act_away, mov_mult=mov_mult
    )

    # Save updated ratings back to dictionary
    franchise_ratings[home_key] = home_rating_after
    franchise_ratings[away_key] = away_rating_after

    # Write history entries
    home_history = TeamRatingHistory(
        team_id=game.home_team_id,
        club_id=home_club_id,
        competition_mapping_id=game.round.competition.competition_mapping_id,
        game_id=game.id,
        rating_before=home_rating_before,
        rating_after=home_rating_after,
        opponent_team_id=game.away_team_id,
        opponent_rating=away_rating_before,
        expected_result=exp_home,
        actual_result=act_home,
        home_advantage_applied=True,
    )

    away_history = TeamRatingHistory(
        team_id=game.away_team_id,
        club_id=away_club_id,
        competition_mapping_id=game.round.competition.competition_mapping_id,
        game_id=game.id,
        rating_before=away_rating_before,
        rating_after=away_rating_after,
        opponent_team_id=game.home_team_id,
        opponent_rating=home_rating_before,
        expected_result=exp_away,
        actual_result=act_away,
        home_advantage_applied=False,
    )

    session.add(home_history)
    session.add(away_history)

    return home_rating_after, away_rating_after


def recalculate_all_ratings(session: Session) -> None:
    """Core recalculation logic, replaying all completed games chronologically."""
    # 1. Fetch all completed games ordered by date
    stmt = (
        select(Game)
        .options(
            joinedload(Game.round).joinedload(Round.competition),
            joinedload(Game.home_team),
            joinedload(Game.away_team),
        )
        .where(Game.status == "completed")
        .order_by(Game.game_date.asc(), Game.id.asc())
    )
    games = session.scalars(stmt).all()
    logger.info(f"Loaded {len(games)} completed games for Elo recalculation.")

    # 2. Track state
    # Key: (club_id, comp_mapping_id) -> rating
    franchise_ratings: dict[tuple[int, int], float] = {}
    # Key: (club_id, comp_mapping_id) -> last season year processed
    franchise_years: dict[tuple[int, int], int] = {}

    processed_count = 0

    for game in games:
        home_club_id = game.home_team.club_id
        away_club_id = game.away_team.club_id
        comp_mapping_id = game.round.competition.competition_mapping_id or 0
        game_year = game.round.competition.year

        home_key = (home_club_id, comp_mapping_id)
        away_key = (away_club_id, comp_mapping_id)

        # Apply season decay if year has incremented
        for key in [home_key, away_key]:
            last_year = franchise_years.get(key)
            if last_year is not None and game_year > last_year:
                old_rating = franchise_ratings.get(key, BASE_RATING)
                decayed_rating = 0.7 * old_rating + 0.3 * BASE_RATING
                franchise_ratings[key] = decayed_rating
                logger.debug(
                    f"Decayed franchise {key} from {old_rating:.1f} to {decayed_rating:.1f} for year {game_year}"
                )
            franchise_years[key] = game_year

        # Process the game
        process_completed_game(session, game, franchise_ratings)
        processed_count += 1

    session.commit()
    logger.info(
        f"Recalculated ratings: processed {processed_count} games, tracked {len(franchise_ratings)} franchises."
    )


def backfill_ratings(session_factory) -> None:
    """One-time migration helper to rebuild the entire ratings history."""
    session = session_factory()
    try:
        logger.info("Truncating team_rating_history...")
        session.execute(
            text("TRUNCATE TABLE team_rating_history RESTART IDENTITY CASCADE")
        )
        session.commit()

        logger.info("Running Elo backfill...")
        recalculate_all_ratings(session)
    except Exception as e:
        session.rollback()
        logger.error(f"Backfill failed: {e}")
        raise e
    finally:
        session.close()


def recalculate_ratings(session_factory) -> None:
    """Recalculate ratings wrapper used by the scheduler."""
    backfill_ratings(session_factory)
    
    # Recalculate player impacts
    from src.core.config import get_settings
    from src.ratings.player_impact_service import recalculate_all_impacts
    settings = get_settings()
    recalculate_all_impacts(session_factory, settings.current_season_year)
