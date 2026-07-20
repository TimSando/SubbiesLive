"""Central model registry — imports all models so SQLAlchemy/Alembic can discover them."""

# Import all models here so that Base.metadata contains all tables
from src.competitions.models import Competition, Round  # noqa: F401
from src.clubs.models import Club, Team  # noqa: F401
from src.games.models import Game, GameEvent  # noqa: F401
from src.players.models import Player  # noqa: F401
from src.notifications.models import PwaSubscription, PwaSubscriptionTopic  # noqa: F401
from src.venues.models import Venue  # noqa: F401
from src.ratings.models import TeamRatingHistory  # noqa: F401
