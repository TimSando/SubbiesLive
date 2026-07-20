from src.ratings.service import get_effective_rating
from src.ratings.elo import HOME_ADVANTAGE_OFFSET


def test_effective_rating_without_home_advantage():
    """Away team should get base rating with no adjustment."""
    result = get_effective_rating(1500.0, is_home=False)
    assert result == 1500.0


def test_effective_rating_with_home_advantage():
    """Home team should get base rating + home advantage offset."""
    result = get_effective_rating(1500.0, is_home=True)
    assert result == 1500.0 + HOME_ADVANTAGE_OFFSET


def test_effective_rating_preserves_base():
    """Effective rating should be additive on top of any base rating."""
    result = get_effective_rating(1650.0, is_home=True)
    assert result == 1650.0 + HOME_ADVANTAGE_OFFSET
