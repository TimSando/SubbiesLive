"""FuseSport API client — adapted from the original fuseSport.py script.

Provides functions to fetch competition, game, and team data from the
FuseSport API (https://api-001.fusesport.com).
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

DEVICE_ID = os.environ.get("FUSESPORT_DEVICE_ID", "8ba924de4b6d5cb0")
BASE_URL = "https://api-001.fusesport.com"


def get_teams():
    """Fetch all teams and extract unique competitions.

    Returns a list of dicts: [{"id": int, "name": str}, ...]
    """
    url = f"{BASE_URL}/teams/search/"
    params = {"device_id": DEVICE_ID}

    logger.info("Fetching teams/competitions from FuseSport...")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    competitions = []
    seen_ids = set()
    for team in r.json():
        comp_id = team["competition"]["id"]
        if comp_id not in seen_ids:
            seen_ids.add(comp_id)
            competitions.append({
                "id": comp_id,
                "name": team["competition"]["name"],
            })

    logger.info(f"Found {len(competitions)} competitions")
    return competitions, r.json()


def get_comp_info(comp_id: int):
    """Fetch full competition info including rounds and games.

    Returns the raw JSON response from FuseSport.
    """
    url = f"{BASE_URL}/comps/{comp_id}/get/"
    params = {"device_id": DEVICE_ID}

    logger.info(f"Fetching competition {comp_id} details...")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_game_info(game_id: int):
    """Fetch detailed game info including score sheets and events.

    Returns the raw JSON response from FuseSport.
    """
    url = f"{BASE_URL}/games/{game_id}/get/"
    params = {"device_id": DEVICE_ID}

    logger.debug(f"Fetching game {game_id} details...")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()
