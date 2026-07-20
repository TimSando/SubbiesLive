import pytest
from src.ratings.player_impact import (
    compute_impact,
    compute_squad_modifier,
    PlayerImpactInput,
    MAX_PLAYER_IMPACT,
)


# --- compute_impact tests ---


def test_impact_low_sample_with():
    """Below MIN_GAMES_WITH threshold → impact 0.0, confidence 'low'."""
    data = PlayerImpactInput(
        games_with=3,
        games_without=10,
        win_rate_with=0.8,
        win_rate_without=0.3,
        avg_margin_with=15.0,
        avg_margin_without=-5.0,
    )
    result = compute_impact(data)
    assert result.impact_score == 0.0
    assert result.confidence == "low"


def test_impact_starter_all_games():
    """Starter playing in all games (games_without = 0) with sufficient games_with should be computed."""
    data = PlayerImpactInput(
        games_with=10,
        games_without=0,
        win_rate_with=0.8,
        win_rate_without=0.5,
        avg_margin_with=15.0,
        avg_margin_without=0.0,
    )
    result = compute_impact(data)
    assert result.impact_score > 0.0
    assert result.confidence == "low"


def test_impact_positive_player():
    """Player with higher win rate when playing → positive impact score."""
    data = PlayerImpactInput(
        games_with=20,
        games_without=10,
        win_rate_with=0.7,
        win_rate_without=0.4,
        avg_margin_with=10.0,
        avg_margin_without=-2.0,
    )
    result = compute_impact(data)
    assert result.impact_score > 0.0
    assert result.confidence in ["medium", "high"]


def test_impact_negative_player():
    """Player with lower win rate when playing → negative impact score."""
    data = PlayerImpactInput(
        games_with=15,
        games_without=15,
        win_rate_with=0.3,
        win_rate_without=0.6,
        avg_margin_with=-5.0,
        avg_margin_without=10.0,
    )
    result = compute_impact(data)
    assert result.impact_score < 0.0


def test_impact_neutral_player():
    """Player with identical with/without stats → near-zero impact."""
    data = PlayerImpactInput(
        games_with=20,
        games_without=20,
        win_rate_with=0.5,
        win_rate_without=0.5,
        avg_margin_with=5.0,
        avg_margin_without=5.0,
    )
    result = compute_impact(data)
    assert abs(result.impact_score) < 1.0


def test_impact_clamped_positive():
    """Extreme positive stats should be clamped to MAX_PLAYER_IMPACT."""
    data = PlayerImpactInput(
        games_with=30,
        games_without=30,
        win_rate_with=1.0,
        win_rate_without=0.0,
        avg_margin_with=50.0,
        avg_margin_without=-50.0,
    )
    result = compute_impact(data)
    assert result.impact_score <= MAX_PLAYER_IMPACT
    assert result.impact_score == MAX_PLAYER_IMPACT


def test_impact_clamped_negative():
    """Extreme negative stats should be clamped to -MAX_PLAYER_IMPACT."""
    data = PlayerImpactInput(
        games_with=30,
        games_without=30,
        win_rate_with=0.0,
        win_rate_without=1.0,
        avg_margin_with=-50.0,
        avg_margin_without=50.0,
    )
    result = compute_impact(data)
    assert result.impact_score >= -MAX_PLAYER_IMPACT
    assert result.impact_score == -MAX_PLAYER_IMPACT


def test_confidence_low():
    """<15 total games → confidence 'low'."""
    data = PlayerImpactInput(
        games_with=8,
        games_without=5,
        win_rate_with=0.6,
        win_rate_without=0.5,
        avg_margin_with=5.0,
        avg_margin_without=3.0,
    )
    result = compute_impact(data)
    assert result.confidence == "low"


def test_confidence_medium():
    """15-29 total games → confidence 'medium'."""
    data = PlayerImpactInput(
        games_with=12,
        games_without=8,
        win_rate_with=0.6,
        win_rate_without=0.5,
        avg_margin_with=5.0,
        avg_margin_without=3.0,
    )
    result = compute_impact(data)
    assert result.confidence == "medium"


def test_confidence_high():
    """30+ total games → confidence 'high'."""
    data = PlayerImpactInput(
        games_with=20,
        games_without=15,
        win_rate_with=0.6,
        win_rate_without=0.5,
        avg_margin_with=5.0,
        avg_margin_without=3.0,
    )
    result = compute_impact(data)
    assert result.confidence == "high"


# --- compute_squad_modifier tests ---


def test_squad_modifier_full_strength():
    """Named squad matching full-strength baseline → modifier 0.0."""
    impact_scores = {1: 20.0, 2: 15.0, 3: 10.0}
    baseline = 45.0  # sum of all three
    modifier = compute_squad_modifier(
        named_squad=[1, 2, 3],
        all_impact_scores=impact_scores,
        full_strength_baseline=baseline,
    )
    assert modifier == pytest.approx(0.0)


def test_squad_modifier_missing_key_player():
    """Dropping the highest-impact player → negative modifier."""
    impact_scores = {1: 30.0, 2: 15.0, 3: 10.0}
    baseline = 55.0  # sum of all three
    modifier = compute_squad_modifier(
        named_squad=[2, 3],  # player 1 missing
        all_impact_scores=impact_scores,
        full_strength_baseline=baseline,
    )
    assert modifier < 0.0
    assert modifier == pytest.approx(-30.0)


def test_squad_modifier_unknown_player():
    """Players not in impact_scores dict should contribute 0.0."""
    impact_scores = {1: 20.0, 2: 15.0}
    baseline = 35.0
    modifier = compute_squad_modifier(
        named_squad=[1, 2, 999],  # 999 is unknown
        all_impact_scores=impact_scores,
        full_strength_baseline=baseline,
    )
    assert modifier == pytest.approx(0.0)


def test_squad_modifier_stronger_than_baseline():
    """If named squad exceeds baseline (e.g. player improved), modifier is positive."""
    impact_scores = {1: 25.0, 2: 20.0}
    baseline = 40.0
    modifier = compute_squad_modifier(
        named_squad=[1, 2],
        all_impact_scores=impact_scores,
        full_strength_baseline=baseline,
    )
    assert modifier > 0.0
    assert modifier == pytest.approx(5.0)
