import pytest
from src.ratings.elo import (
    expected_score,
    update_rating,
    margin_of_victory_multiplier,
    win_probability_to_odds,
    predict_match,
)

# --- expected_score tests ---


def test_expected_score_equal_ratings():
    """Two equally rated teams should have 0.5 expected score."""
    result = expected_score(1500.0, 1500.0)
    assert result == pytest.approx(0.5)


def test_expected_score_higher_rated_team():
    """A 200-point gap should give ~0.76 for the stronger team."""
    result = expected_score(1600.0, 1400.0)
    assert result == pytest.approx(0.76, abs=0.01)


def test_expected_score_lower_rated_team():
    """The weaker team's expected score should be ~0.24."""
    result = expected_score(1400.0, 1600.0)
    assert result == pytest.approx(0.24, abs=0.01)


def test_expected_score_large_gap():
    """A 400-point gap should give ~0.91 for the stronger team."""
    result = expected_score(1700.0, 1300.0)
    assert result == pytest.approx(0.91, abs=0.01)


def test_expected_score_symmetry():
    """expected_score(A, B) + expected_score(B, A) should equal 1.0."""
    a = expected_score(1550.0, 1450.0)
    b = expected_score(1450.0, 1550.0)
    assert a + b == pytest.approx(1.0)


# --- update_rating tests ---


def test_update_rating_expected_win():
    """Winning as expected should produce a small rating increase."""
    expected = expected_score(1600.0, 1400.0)  # ~0.76
    new_rating = update_rating(
        1600.0, expected, actual=1.0, k_factor=32.0, mov_mult=1.0
    )
    change = new_rating - 1600.0
    assert 0 < change < 10  # Small increase


def test_update_rating_upset_win():
    """Winning as the underdog should produce a large rating increase."""
    expected = expected_score(1400.0, 1600.0)  # ~0.24
    new_rating = update_rating(
        1400.0, expected, actual=1.0, k_factor=32.0, mov_mult=1.0
    )
    change = new_rating - 1400.0
    assert change > 20  # Large increase for upset


def test_update_rating_loss():
    """Losing should decrease the rating."""
    expected = expected_score(1500.0, 1500.0)  # 0.5
    new_rating = update_rating(
        1500.0, expected, actual=0.0, k_factor=32.0, mov_mult=1.0
    )
    assert new_rating < 1500.0


def test_update_rating_draw():
    """A draw between equal teams should not change ratings."""
    expected = expected_score(1500.0, 1500.0)  # 0.5
    new_rating = update_rating(
        1500.0, expected, actual=0.5, k_factor=32.0, mov_mult=1.0
    )
    assert new_rating == pytest.approx(1500.0)


def test_update_rating_zero_sum():
    """Rating changes for both teams should be equal and opposite (before MoV)."""
    exp_a = expected_score(1500.0, 1500.0)
    exp_b = expected_score(1500.0, 1500.0)
    new_a = update_rating(1500.0, exp_a, actual=1.0, k_factor=32.0, mov_mult=1.0)
    new_b = update_rating(1500.0, exp_b, actual=0.0, k_factor=32.0, mov_mult=1.0)
    assert (new_a - 1500.0) == pytest.approx(-(new_b - 1500.0))


# --- margin_of_victory_multiplier tests ---


def test_mov_multiplier_close_game():
    """A 1-point margin should give a multiplier near 1.0 (minimal scaling)."""
    mult = margin_of_victory_multiplier(score_diff=1, elo_diff=0.0)
    assert 0.5 < mult <= 1.2


def test_mov_multiplier_blowout():
    """A 50-point blowout should give a multiplier > 1.0 but capped."""
    mult = margin_of_victory_multiplier(score_diff=50, elo_diff=0.0)
    assert mult > 1.0
    assert mult < 3.0  # Should be capped to prevent runaway ratings


def test_mov_multiplier_zero_diff():
    """A draw (0-point diff) should give a minimal multiplier."""
    mult = margin_of_victory_multiplier(score_diff=0, elo_diff=0.0)
    assert mult >= 0.0
    assert mult <= 1.0


def test_mov_multiplier_increases_with_margin():
    """Larger margins should give larger multipliers."""
    mult_small = margin_of_victory_multiplier(score_diff=5, elo_diff=0.0)
    mult_large = margin_of_victory_multiplier(score_diff=30, elo_diff=0.0)
    assert mult_large > mult_small


# --- win_probability_to_odds tests ---


def test_odds_even():
    """50% probability should give '1:1'."""
    assert win_probability_to_odds(0.5) == "1:1"


def test_odds_strong_favourite():
    """75% probability should give '3:1'."""
    assert win_probability_to_odds(0.75) == "3:1"


def test_odds_two_thirds():
    """~67% probability should give '2:1'."""
    assert win_probability_to_odds(0.667) == "2:1"


def test_odds_underdog():
    """25% probability should give '1:3'."""
    assert win_probability_to_odds(0.25) == "1:3"


def test_odds_extreme():
    """90%+ probability should produce high fractional odds."""
    result = win_probability_to_odds(0.9)
    assert ":" in result


# --- predict_match tests ---


def test_predict_match_probabilities_sum_to_one():
    """Home + Away + Draw probabilities must sum to 1.0."""
    result = predict_match(1500.0, 1500.0, home_advantage=40.0)
    total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
    assert total == pytest.approx(1.0, abs=0.01)


def test_predict_match_home_advantage():
    """Home advantage should shift probability toward the home team."""
    no_adv = predict_match(1500.0, 1500.0, home_advantage=0.0)
    with_adv = predict_match(1500.0, 1500.0, home_advantage=40.0)
    assert with_adv["home_prob"] > no_adv["home_prob"]
    assert with_adv["away_prob"] < no_adv["away_prob"]


def test_predict_match_stronger_team_favoured():
    """The higher-rated team should have the higher win probability."""
    result = predict_match(1600.0, 1400.0, home_advantage=0.0)
    assert result["home_prob"] > result["away_prob"]


def test_predict_match_draw_probability_small():
    """Draw probability should be small but non-zero."""
    result = predict_match(1500.0, 1500.0, home_advantage=0.0)
    assert 0.01 < result["draw_prob"] < 0.10


def test_predict_match_includes_odds_display():
    """Result should contain fractional odds strings."""
    result = predict_match(1600.0, 1400.0, home_advantage=40.0)
    assert "home_odds_display" in result
    assert "away_odds_display" in result
    assert ":" in result["home_odds_display"]
    assert ":" in result["away_odds_display"]
