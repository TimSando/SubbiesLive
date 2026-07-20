"""Pure mathematical functions for Elo rating updates and match prediction."""

import math

BASE_RATING = 1500.0
DEFAULT_K_FACTOR = 32.0
HOME_ADVANTAGE_OFFSET = 40.0
SEASON_DECAY_FACTOR = 0.7
FIXED_DRAW_PROBABILITY = 0.03


def expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate the expected score (win probability) for rating_a against rating_b."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def margin_of_victory_multiplier(score_diff: int, elo_diff: float) -> float:
    """Scale Elo rating updates by margin of victory to prevent inflation from blowouts."""
    # Ensure non-negative score difference
    abs_diff = abs(score_diff)
    # Natural log scaling
    return math.log(abs_diff + 1.0) * 0.6 + 0.3


def update_rating(
    rating: float,
    expected: float,
    actual: float,
    k_factor: float = DEFAULT_K_FACTOR,
    mov_mult: float = 1.0,
) -> float:
    """Calculate the updated rating for a team."""
    return rating + k_factor * mov_mult * (actual - expected)


def win_probability_to_odds(probability: float) -> str:
    """Convert win probability (0.0 to 1.0) to fractional odds representation (e.g. '3:1')."""
    if probability >= 1.0:
        return "99:1"
    if probability <= 0.0:
        return "1:99"

    is_underdog = probability < 0.5
    p = 1.0 - probability if is_underdog else probability

    ratio = p / (1.0 - p)
    rounded_ratio = round(ratio)
    if rounded_ratio < 1:
        rounded_ratio = 1

    if is_underdog:
        return f"1:{rounded_ratio}"
    else:
        return f"{rounded_ratio}:1"


def predict_match(
    home_rating: float,
    away_rating: float,
    home_advantage: float = HOME_ADVANTAGE_OFFSET,
) -> dict:
    """Predict a match outcome and return probabilities and odds."""
    # Apply home advantage to get effective home rating
    effective_home_rating = home_rating + home_advantage

    # Expected home score (probability of home win if no draws)
    expected_home = expected_score(effective_home_rating, away_rating)

    # Adjust for draw probability
    draw_prob = FIXED_DRAW_PROBABILITY
    home_prob = expected_home * (1.0 - draw_prob)
    away_prob = (1.0 - expected_home) * (1.0 - draw_prob)

    # Convert to odds
    home_odds = win_probability_to_odds(home_prob)
    away_odds = win_probability_to_odds(away_prob)

    return {
        "home_prob": home_prob,
        "away_prob": away_prob,
        "draw_prob": draw_prob,
        "home_odds_display": home_odds,
        "away_odds_display": away_odds,
    }
