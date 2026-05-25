import os
import json
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from src.ingestion.engine import get_sync_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Manual aliases for team matching
ALIASES = {
    "two blues": ["western sydney two blues", "two blues 2"],
    "lc old ignatians": ["lane cove", "old ignatians", "lane cove / old ignatians", "lc old igs"],
    "unsw": ["unsw", "university of new south wales", "unsw/es"],
    "macquarie uni": ["macquarie university"],
    "sydney uni": ["sydney university", "sydney uni sirens", "syd uni"],
    "wakehurst/old barker": ["wakehurst", "old barker", "wakehurst / old barker"],
    "colleagues ii": ["colleagues"],
    "manly savers": ["manly savers savers", "savers", "manly"],
    "easts": ["eastern suburbs", "easts 2", "easts 5th grade"],
    "gordon": ["gordon 2", "gordon*"],
    "wollongong": ["uni of wollongong", "university of wollongong", "wollongong university"],
    "brothers": ["brothers 2nds"],
    "chatswood": ["chatswood 2nds"],
    "briars": ["briars 2nds"],
    "kings": ["kings 2nds"],
    "forest": ["forest 5ths"],
    "hills": ["hills 2nds"],
    "lindfield": ["lindfield 5ths"],
    "macquarie uni": ["macquarie uni 2nds"],
    "manly savers": ["manly savers 2nds", "manly savers colts"],
    "mosman": ["mosman 6ths"],
    "newport": ["newport 5ths"],
    "sydney convicts": ["sydney convicts 2nds"],
}

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

def match_team_names(db_team: str, scraped_team: str) -> tuple[bool, bool]:
    """
    Compare DB team name and scraped team name.
    Returns (is_match, needs_review).
    """
    db_clean = clean_team_name(db_team)
    scraped_clean = clean_team_name(scraped_team)
    
    if not db_clean or not scraped_clean:
        return False, True
        
    # 1. Exact match after cleaning
    if db_clean == scraped_clean:
        return True, False
        
    # 2. Check aliases
    for base_alias, variants in ALIASES.items():
        if db_clean == base_alias and scraped_clean in variants:
            return True, False
        if scraped_clean == base_alias and db_clean in variants:
            return True, False
            
    # 3. Substring match (e.g. "two blues" in "western sydney two blues")
    if db_clean in scraped_clean or scraped_clean in db_clean:
        # A substring match is a match, but let's flag as needs_review if names are quite different
        needs_review = len(db_clean) < len(scraped_clean) * 0.6 or len(scraped_clean) < len(db_clean) * 0.6
        return True, needs_review
        
    # 4. Token overlap matching
    db_tokens = set(db_clean.split())
    scraped_tokens = set(scraped_clean.split())
    common_tokens = db_tokens.intersection(scraped_tokens)
    
    # If they share significant words (excluding small words like 'of', 'the')
    filtered_common = {t for t in common_tokens if len(t) > 3}
    if filtered_common:
        return True, True  # Match found but requires review
        
    return False, True

def parse_scraped_datetime(date_str: str, time_str: str):
    """Parse date and time strings from NSWRugbyTV to naive datetime."""
    try:
        # Format: "Saturday 25 Apr 2026"
        parts = date_str.strip().split()
        if len(parts) >= 4:
            clean_date_str = " ".join(parts[1:4]) # "25 Apr 2026"
            game_date = datetime.strptime(clean_date_str, "%d %b %Y").date()
        else:
            return None
            
        # Format: "3:15 PM"
        t_parts = time_str.strip().split()
        if len(t_parts) >= 2:
            parsed_time = datetime.strptime(time_str.strip(), "%I:%M %p").time()
        else:
            parsed_time = datetime.min.time()
            
        return datetime.combine(game_date, parsed_time)
    except Exception as e:
        logger.debug(f"Failed to parse datetime '{date_str}' / '{time_str}': {e}")
        return None

def ingest_nswrugbytv_videos(engine=None):
    if engine is None:
        engine = get_sync_engine()
        
    logger.info("Starting NSWRugbyTV video URL ingestion...")
    
    # 1. Load competition seeds
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "nswrugbytv_competitions.json")
    
    if not os.path.exists(config_path):
        logger.error(f"Seeding config file not found at {config_path}. Run discovery script first.")
        return
        
    with open(config_path, "r") as f:
        competitions_seed = json.load(f)
        
    # 2. Query all upcoming & completed games for our competitions
    # We load them to match in memory to keep DB operations clean
    with engine.connect() as conn:
        # Fetch games with team names and competition name
        query = text("""
            SELECT g.id, g.game_date, g.status, 
                   t_home.name AS home_team_name, t_away.name AS away_team_name,
                   c.name AS competition_name, c.id AS competition_id
            FROM games g
            JOIN rounds r ON g.round_id = r.id
            JOIN competitions c ON r.competition_id = c.id
            JOIN teams t_home ON g.home_team_id = t_home.id
            JOIN teams t_away ON g.away_team_id = t_away.id
            WHERE g.game_date >= NOW() - INTERVAL '180 days'
        """)
        db_games = [dict(row) for row in conn.execute(query).mappings()]
        
    logger.info(f"Loaded {len(db_games)} database games from the last 180 days to match against.")
    
    matched_count = 0
    updated_count = 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 3. Fetch each competition page and scrape matches
    for comp in competitions_seed:
        comp_uuid = comp["competitionuuid"]
        comp_name = comp["competition_name"]
        
        logger.info(f"Scraping competition '{comp_name}' (UUID: {comp_uuid})...")
        url = f"https://nswrugbytv.com.au/2026-match-centre-competition/?competitionuuid={comp_uuid}&limit=500"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch competition page {comp_uuid}: HTTP {r.status_code}")
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.find_all(class_="nsw-fixture-card")
            logger.info(f"Found {len(cards)} fixture cards on page.")
            
            for card in cards:
                # Extract watch replay link / matchuuid
                watch_replay_link = card.find(class_="nsw-watch-replay")
                share_btn = card.find(class_="js-nsw-share")
                
                match_uuid = None
                if watch_replay_link and "matchuuid=" in watch_replay_link.get("href", ""):
                    href = watch_replay_link["href"]
                    # Extract UUID from query param
                    match_uuid = href.split("matchuuid=")[-1].split("&")[0]
                elif share_btn and share_btn.get("data-matchuuid"):
                    match_uuid = share_btn["data-matchuuid"]
                    
                if not match_uuid:
                    # No video available for this match
                    continue
                    
                video_url = f"https://nswrugbytv.com.au/2026-match-detail/?matchuuid={match_uuid}"
                
                # Extract team names
                home_team_elem = card.find(class_="nsw-team-home")
                away_team_elem = card.find(class_="nsw-team-away")
                
                home_name = ""
                away_name = ""
                if home_team_elem:
                    name_link = home_team_elem.find(class_="nsw-team-name-link")
                    home_name = name_link.get_text(strip=True) if name_link else ""
                if away_team_elem:
                    name_link = away_team_elem.find(class_="nsw-team-name-link")
                    away_name = name_link.get_text(strip=True) if name_link else ""
                    
                # Extract date and time
                date_elem = card.find(class_="nsw-fixture-date")
                time_elem = card.find(class_="nsw-fixture-time")
                
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                time_str = time_elem.get_text(strip=True) if time_elem else ""
                
                scraped_dt = parse_scraped_datetime(date_str, time_str)
                if not scraped_dt:
                    continue
                    
                # 4. Find the matching game in the DB
                best_match = None
                best_confidence_review = True
                
                for g in db_games:
                    # Compare date window (within 4 hours)
                    time_diff = abs((g["game_date"] - scraped_dt).total_seconds())
                    if time_diff > 4 * 3600:
                        continue
                        
                    # Compare home & away team names
                    home_match, home_review = match_team_names(g["home_team_name"], home_name)
                    away_match, away_review = match_team_names(g["away_team_name"], away_name)
                    
                    if home_match and away_match:
                        best_match = g
                        # Needs review if either team mapping was flagged
                        best_confidence_review = home_review or away_review
                        break
                        
                if best_match:
                    matched_count += 1
                    # Save video URL to database
                    with engine.begin() as transaction_conn:
                        transaction_conn.execute(
                            text("""
                                UPDATE games 
                                SET video_url = :video_url, 
                                    video_url_needs_review = :needs_review
                                WHERE id = :game_id
                            """),
                            {
                                "video_url": video_url,
                                "needs_review": best_confidence_review,
                                "game_id": best_match["id"]
                            }
                        )
                    updated_count += 1
                    logger.info(f"Matched & updated game {best_match['id']}: "
                                f"{best_match['home_team_name']} vs {best_match['away_team_name']} "
                                f"(Needs Review: {best_confidence_review})")
                    
        except Exception as e:
            logger.error(f"Error processing competition {comp_uuid}: {e}", exc_info=True)
            
    logger.info(f"NSWRugbyTV ingestion completed. Total matched matches: {matched_count}, DB Updates: {updated_count}")

if __name__ == "__main__":
    ingest_nswrugbytv_videos()
