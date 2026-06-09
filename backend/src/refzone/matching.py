from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional

# Manual aliases for team matching
ALIASES = {
    "two blues": ["western sydney two blues", "two blues 2"],
    "lc old ignatians": [
        "lane cove",
        "old ignatians",
        "lane cove / old ignatians",
        "lc old igs",
    ],
    "unsw": ["unsw", "university of new south wales", "unsw/es"],
    "macquarie uni": ["macquarie university", "macquarie uni 2nds"],
    "sydney uni": ["sydney university", "sydney uni sirens", "syd uni"],
    "wakehurst/old barker": ["wakehurst", "old barker", "wakehurst / old barker"],
    "colleagues ii": ["colleagues"],
    "manly savers": [
        "manly savers savers",
        "savers",
        "manly",
        "manly savers 2nds",
        "manly savers colts",
    ],
    "easts": ["eastern suburbs", "easts 2", "easts 5th grade"],
    "gordon": ["gordon 2", "gordon*"],
    "wollongong": [
        "uni of wollongong",
        "university of wollongong",
        "wollongong university",
    ],
    "brothers": ["brothers 2nds"],
    "chatswood": ["chatswood 2nds"],
    "briars": ["briars 2nds"],
    "kings": ["kings 2nds"],
    "forest": ["forest 5ths"],
    "hills": ["hills 2nds"],
    "lindfield": ["lindfield 5ths"],
    "mosman": ["mosman 6ths"],
    "newport": ["newport 5ths"],
    "sydney convicts": ["sydney convicts 2nds"],
}

try:
    from zoneinfo import ZoneInfo

    SYDNEY_TZ = ZoneInfo("Australia/Sydney")
except ImportError:
    SYDNEY_TZ = timezone(timedelta(hours=10))


def clean_team_name(name: str) -> str:
    """Normalize team name for matching."""
    if not name:
        return ""
    # Remove division/competition suffix in DB team names (e.g. "Colleagues - Kentwell Cup")
    if " - " in name:
        name = name.split(" - ")[0]
    name = name.lower().strip()

    # Remove common suffixes
    for suffix in ["rufc", "rfc", "rugby", "club", "premiership"]:
        name = name.replace(suffix, "")

    # Normalize common synonyms
    name = name.replace("university", "uni")
    name = name.replace("women's", "womens")
    return " ".join(name.split())


# Dynamically clean the ALIASES keys and values to ensure matched lookups work after cleaning.
CLEANED_ALIASES = {
    clean_team_name(key): [clean_team_name(val) for val in val_list]
    for key, val_list in ALIASES.items()
}


def match_team_names(db_team: str, app_team: str) -> Tuple[bool, bool]:
    """Compare DB team name and appointment team name.

    Returns (is_match, needs_review).
    """
    db_clean = clean_team_name(db_team)
    app_clean = clean_team_name(app_team)

    if not db_clean or not app_clean:
        return False, True

    # 1. Exact match after cleaning
    if db_clean == app_clean:
        return True, False

    # 2. Check aliases
    for base_alias, variants in CLEANED_ALIASES.items():
        if db_clean == base_alias and app_clean in variants:
            return True, False
        if app_clean == base_alias and db_clean in variants:
            return True, False

    # 3. Substring match (e.g. "two blues" in "western sydney two blues")
    if db_clean in app_clean or app_clean in db_clean:
        needs_review = (
            len(db_clean) < len(app_clean) * 0.6 or len(app_clean) < len(db_clean) * 0.6
        )
        return True, needs_review

    # 4. Token overlap matching
    db_tokens = set(db_clean.split())
    app_tokens = set(app_clean.split())
    common_tokens = db_tokens.intersection(app_tokens)

    # If they share significant words (excluding small words like 'of', 'the')
    filtered_common = {t for t in common_tokens if len(t) > 3}
    if filtered_common:
        return True, True  # Match found but requires review

    return False, True


def parse_rx_moment_to_sydney(moment_val: Any) -> Optional[datetime]:
    """Parse a RugbyXplorer moment timestamp or string into a naive datetime in Sydney local time."""
    if moment_val is None:
        return None
    try:
        if isinstance(moment_val, (int, float)):
            if moment_val > 1e11:
                moment_val = moment_val / 1000.0
            dt_utc = datetime.fromtimestamp(moment_val, tz=timezone.utc)
            return dt_utc.astimezone(SYDNEY_TZ).replace(tzinfo=None)

        if isinstance(moment_val, str) and moment_val.isdigit():
            val = float(moment_val)
            if val > 1e11:
                val = val / 1000.0
            dt_utc = datetime.fromtimestamp(val, tz=timezone.utc)
            return dt_utc.astimezone(SYDNEY_TZ).replace(tzinfo=None)

        from dateutil import parser as dateparser

        dt = dateparser.parse(str(moment_val))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(SYDNEY_TZ).replace(tzinfo=None)
    except Exception:
        return None


def match_competition_names(db_comp: str, app_comp: str) -> bool:
    """Compare competition names. Case-insensitive substring match.

    If either name is missing, default to True so we don't block matching.
    """
    if not db_comp or not app_comp:
        return True
    db_clean = db_comp.lower().strip()
    app_clean = app_comp.lower().strip()
    return db_clean in app_clean or app_clean in db_clean


def find_matching_game(
    app_moment: Optional[datetime],
    app_home_team: str,
    app_away_team: str,
    db_games: List[Dict[str, Any]],
    app_competition_name: Optional[str] = None,
    time_window_minutes: float = 45.0,
) -> Optional[int]:
    """Find a matching game in the list of db_games.

    Returns the db_game_id (int) or None if no match is found.
    """
    if not app_moment or not app_home_team or not app_away_team:
        return None

    for game in db_games:
        game_date = game.get("game_date")
        if not game_date:
            continue

        # Compare time window (45 minutes by default)
        time_diff = abs((game_date - app_moment).total_seconds())
        if time_diff > time_window_minutes * 60:
            continue

        # Match team names
        home_match, _ = match_team_names(game.get("home_team_name", ""), app_home_team)
        away_match, _ = match_team_names(game.get("away_team_name", ""), app_away_team)

        if home_match and away_match:
            return game.get("id")

    return None
