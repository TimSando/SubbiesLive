import sys
import logging
import re
from sqlalchemy.orm import sessionmaker
from src.ingestion.engine import get_sync_engine
from src.venues.models import Venue
from src.games.models import Game
from src.clubs.models import Club
import src.core.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clean_venues")

# Heuristics for invalid locations (to be completely deleted)
INVALID_PATTERNS = [
    re.compile(r"forfeit", re.I),
    re.compile(r"postpone", re.I),
    re.compile(r"washed\s*out", re.I),
    re.compile(r"withdraw", re.I),
    re.compile(r"cancel", re.I),
    re.compile(r"no\s*match", re.I),
    re.compile(r"null\s*game", re.I),
    re.compile(r"abandoned", re.I),
    re.compile(r"suspended", re.I),
    re.compile(r"wet\s*weather", re.I),
    re.compile(r"already\s*played", re.I),
    re.compile(r"double\s*pts", re.I),
    re.compile(r"cluch\s*tv", re.I),
    re.compile(r"not\s*played", re.I),
]

# Whole word/exact matches that are invalid
INVALID_EXACT = {
    "tbc",
    "venue tbc",
    "venue, date, time tbc",
    "time tbc",
    "bye",
    "bye / no game",
    "no game",
    "tbd",
    "already played",
}

# Regex to clean final prefixes like Mjr SF, Mnr SF, GF1/2, QFA/B, SFA/B, or TBC prefix
CLEANUP_PREFIX_PATTERN = re.compile(
    r"^(?:mjr\s+sf|mnr\s+sf|gf\d+|qf\w|sf\w|(?:time\s+)?tbc)\s*[-:]\s*(.*)", re.I
)


def is_invalid_venue(name: str) -> bool:
    name_lower = name.lower().strip()

    # Check exact/whole-phrase invalid sets
    if name_lower in INVALID_EXACT:
        return True

    # Check if name contains any of the pattern strings
    for pattern in INVALID_PATTERNS:
        if pattern.search(name_lower):
            return True

    # Whole-word check for 'tbc' or 'bye'
    words = re.findall(r"\b\w+\b", name_lower)
    if "tbc" in words or "bye" in words or "tbd" in words:
        return True

    return False


def clean_venues(commit: bool = False):
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        venues = session.query(Venue).order_by(Venue.name).all()
        invalid_venues = []
        remap_venues = []  # list of tuples: (dirty_venue, clean_name)

        for v in venues:
            if is_invalid_venue(v.name):
                invalid_venues.append(v)
                continue

            # Check if it has a prefix that needs cleaning
            match = CLEANUP_PREFIX_PATTERN.match(v.name)
            if match:
                clean_name = match.group(1).strip()
                remap_venues.append((v, clean_name))

        print(f"\n=== Found {len(invalid_venues)} Invalid Venues for Deletion ===")
        for iv in invalid_venues:
            game_ref_count = session.query(Game).filter(Game.venue_id == iv.id).count()
            club_ref_count = (
                session.query(Club).filter(Club.primary_venue_id == iv.id).count()
            )
            print(
                f"- ID: {iv.id:3d} | '{iv.name}' (Games: {game_ref_count}, Clubs: {club_ref_count})"
            )

        print(
            f"\n=== Found {len(remap_venues)} Venues with Final/TBC Prefixes for Remapping ==="
        )
        for dv, clean_name in remap_venues:
            # Check if clean venue already exists
            cv = session.query(Venue).filter(Venue.name == clean_name).first()
            game_ref_count = session.query(Game).filter(Game.venue_id == dv.id).count()
            club_ref_count = (
                session.query(Club).filter(Club.primary_venue_id == dv.id).count()
            )

            if cv:
                print(
                    f"- ID: {dv.id:3d} | '{dv.name}' -> Remap to existing clean Venue '{clean_name}' (ID: {cv.id}) (Games: {game_ref_count}, Clubs: {club_ref_count})"
                )
            else:
                print(
                    f"- ID: {dv.id:3d} | '{dv.name}' -> Rename to new clean Venue '{clean_name}' (Games: {game_ref_count}, Clubs: {club_ref_count})"
                )

        if not invalid_venues and not remap_venues:
            print("\nNo invalid or dirty venues found.")
            return

        if not commit:
            print("\nDRY RUN: Run with --commit to apply deletions and remapping.")
            return

        print("\nCommitting changes...")

        # 1. Process completely invalid venues (Delete & Nullify)
        for iv in invalid_venues:
            session.query(Game).filter(Game.venue_id == iv.id).update(
                {Game.venue_id: None}
            )
            session.query(Club).filter(Club.primary_venue_id == iv.id).update(
                {Club.primary_venue_id: None}
            )
            session.delete(iv)

        # 2. Process prefixed venues (Remap or Rename)
        for dv, clean_name in remap_venues:
            cv = session.query(Venue).filter(Venue.name == clean_name).first()
            if cv:
                # Remap games and clubs to existing clean venue
                session.query(Game).filter(Game.venue_id == dv.id).update(
                    {Game.venue_id: cv.id}
                )
                session.query(Club).filter(Club.primary_venue_id == dv.id).update(
                    {Club.primary_venue_id: cv.id}
                )
                # Delete the dirty venue
                session.delete(dv)
            else:
                # Rename the dirty venue to the clean name and reset coordinates (so it backfills)
                dv.name = clean_name
                dv.latitude = None
                dv.longitude = None

        session.commit()
        print(f"\nSuccessfully cleaned and remapped all venues.")

    except Exception as e:
        session.rollback()
        logger.error(f"Error during cleanup: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    should_commit = "--commit" in sys.argv
    clean_venues(commit=should_commit)
