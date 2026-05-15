"""Data transformation — maps raw FuseSport API responses into database-ready dicts."""

import logging
from datetime import datetime
from dateutil import parser as dateparser

logger = logging.getLogger(__name__)


import re

def extract_club_name(team_name: str) -> str | None:
    """Extract the club name from a FuseSport team name.

    e.g., "Mosman - Kentwell Cup" -> "Mosman"
          "Blue Mountains - Barbour Cup (Colts)" -> "Blue Mountains"
          
    Also filters out invalid club names and duplicates like "2nds", returning None.
    """
    raw_name = team_name
    if " - " in team_name:
        raw_name = team_name.split(" - ")[0].strip()
    else:
        raw_name = team_name.strip()
        
    # Invalid markers to ignore completely
    invalid_exact = {"Wet Weather Week", "Blank", "King's Birthday", "Anzac Day", ""}
    if raw_name in invalid_exact:
        return None
        
    if re.search(r'(?i)^Rd \d+ published soon', raw_name) or re.search(r'(?i)^draw to be published', raw_name):
        return None

    # Remove trailing numbers/grades/colts like " 2nds", " 6ths", " II", " 2", " Colts", " 5th Grade"
    # Matches patterns like "Balmain 2nds", "Colleagues II", "Manly 2", "Gordon*", "Colleagues Colts", "Easts 5th Grade"
    cleaned_name = re.sub(r'(?i)\s+(?:[1-6]ths|[1-6]sts|[1-6]nds|[1-6]rds|II|IV|V|VI|[1-6]|Colts|[1-6]th Grade|\*)$', '', raw_name).strip()
    # also remove trailing asterisks and remaining dash artifacts if any
    cleaned_name = re.sub(r'\*$', '', cleaned_name).strip()
    
    return cleaned_name if cleaned_name else None


def parse_game_date(datestr: str) -> datetime | None:
    """Parse a game date string into a datetime object."""
    if not datestr:
        return None
    try:
        return dateparser.parse(datestr)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {datestr}")
        return None


def determine_game_status(game: dict) -> str:
    """Determine game status from FuseSport game data."""
    if game.get("submitted"):
        return "completed"
    game_date = parse_game_date(game.get("gamedate", ""))
    if game_date and game_date < datetime.now():
        return "in_progress"
    return "scheduled"


def extract_round_number(round_name: str) -> int | None:
    """Extract numeric round number from round name.

    e.g., "Round 1" -> 1, "Semi Final" -> None, "BYE" -> None
    """
    if round_name.startswith("Round "):
        try:
            return int(round_name.replace("Round ", ""))
        except ValueError:
            pass
    return None


def map_event_type(fusesport_slug: str) -> str:
    """Map FuseSport event type slugs to our simplified event types."""
    mapping = {
        "rugby_union_try": "try",
        "rugby_union_conversion": "conversion",
        "rugby_union_penalty_goal": "penalty_goal",
        "rugby_union_drop_goal": "drop_goal",
        "rugby_union_yellow_card": "yellow_card",
        "rugby_union_red_card": "red_card",
    }
    return mapping.get(fusesport_slug, fusesport_slug)


def transform_team(raw_team: dict) -> dict:
    """Transform a raw FuseSport team into our schema."""
    return {
        "external_id": raw_team["id"],
        "name": raw_team.get("name", ""),
        "club_name": extract_club_name(raw_team.get("team_name", raw_team.get("name", ""))),
        "logo_url": raw_team.get("logo_url"),
    }


def transform_game(raw_game: dict, round_external_id: int) -> dict:
    """Transform a raw FuseSport game into our schema."""
    return {
        "external_id": raw_game["id"],
        "round_external_id": round_external_id,
        "game_date": parse_game_date(raw_game.get("gamedate", "")),
        "home_team_external_id": raw_game["hmteam"]["id"],
        "away_team_external_id": raw_game["awteam"]["id"],
        "home_team": transform_team(raw_game["hmteam"]),
        "away_team": transform_team(raw_game["awteam"]),
        "location": raw_game.get("location"),
        "home_score": raw_game.get("hmscore"),
        "away_score": raw_game.get("awscore"),
        "status": determine_game_status(raw_game),
    }


def transform_game_event(raw_event: dict, game_external_id: int) -> dict:
    """Transform a raw FuseSport game event into our schema."""
    event_type_info = raw_event.get("event_type", {})

    result = {
        "external_id": raw_event.get("id"),
        "game_external_id": game_external_id,
        "team_external_id": raw_event.get("team_id"),
        "event_type": map_event_type(event_type_info.get("slug", "")),
        "player_number": raw_event.get("player_number"),
        "points": event_type_info.get("points", 0),
        "text": raw_event.get("text", ""),
        "external_created_at": parse_game_date(raw_event.get("created", "")),
    }

    # Player info (may be null for away team events on home score sheet)
    member = raw_event.get("member")
    if member:
        result["player"] = {
            "external_id": member["id"],
            "name": member.get("name", ""),
            "dob": member.get("dob"),
            "image_url": member.get("image"),
            "thumbnail_url": member.get("thumbnail"),
        }
    else:
        result["player"] = None

    return result
