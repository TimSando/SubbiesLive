import os
import json
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrich_club_socials")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Custom overrides for prominent/uniquely-named clubs or generic collision fixes
CLUB_OVERRIDES = {
    "Colleagues": {
        "fb": "https://www.facebook.com/ColleaguesRugby",
        "ig": "https://www.instagram.com/colleaguesrugby",
    },
    "Randwick": {
        "fb": "https://www.facebook.com/RandwickRugby",
        "ig": "https://www.instagram.com/randwickrugby",
    },
    "Barker Old Boys": {
        "fb": "https://www.facebook.com/bobsgrizzlies",
        "ig": "https://www.instagram.com/bobsgrizzlies",
    },
    "Sydney University": {
        "fb": "https://www.facebook.com/suprc",
        "ig": "https://www.instagram.com/sydneyunirugby",
    },
    "Northern Suburbs": {
        "fb": "https://www.facebook.com/northsrugby",
        "ig": "https://www.instagram.com/northsrugby",
    },
    "Manly Savers": {
        "fb": "https://www.facebook.com/manlysavers",
        "ig": "https://www.instagram.com/manlysavers",
    },
    "St Patrick's": {
        "fb": "https://www.facebook.com/sprc.com.au",
        "ig": "https://www.instagram.com/stpatsrugby",
    },
    "Campbelltown": {
        "fb": "https://www.facebook.com/campbelltownharlequins",
        "ig": "https://www.instagram.com/campbelltownharlequins",
    },
    "Penrith Emus": {
        "fb": "https://www.facebook.com/penrithemus",
        "ig": "https://www.instagram.com/penrith_emus",
    },
    "Alexandria Dukes": {
        "fb": "https://www.facebook.com/AlexandriaDukesRUFC",
        "ig": "https://www.instagram.com/alexandriadukes",
    },
    "Brothers": {
        "fb": "https://www.facebook.com/brothersrugbysydney",
        "ig": "https://www.instagram.com/brothersrugbyclubsydney",
        "tk": None,
    },
    "Forest": {
        "fb": "https://www.facebook.com/ForestRugby/",
        "ig": "https://www.instagram.com/forestrugby",
        "tk": None,
    },
    "Kings": {
        "fb": "https://www.facebook.com/KingsOldBoysRugby",
        "ig": None,
        "tk": None,
    },
    "Renegades": {
        "fb": "https://www.facebook.com/RouseHillRugby",
        "ig": "https://www.instagram.com/rousehillrenegadesrugby",
        "tk": "https://www.tiktok.com/@rousehillrenegadesrugby",
    },
    "Sydney Harbour": {
        "web": "https://oystersrugby.com",
        "fb": "https://www.facebook.com/oystersrugby",
        "ig": "https://www.instagram.com/oysters.rugby",
        "tk": None,
    },
    "Souths": {
        "fb": "https://www.facebook.com/southerndistrictsrugby",
        "ig": "https://www.instagram.com/southerndistrictsrugby",
        "tk": None,
    },
    "Wests": {
        "fb": "https://www.facebook.com/westharbourrugby",
        "ig": "https://www.instagram.com/westharbourrugby",
        "tk": None,
    },
    "West Harbour": {
        "fb": "https://www.facebook.com/westharbourrugby",
        "ig": "https://www.instagram.com/westharbourrugby",
        "tk": None,
    },
    "Wildfires": {
        "fb": "https://www.facebook.com/HunterWildfires",
        "ig": "https://www.instagram.com/hunterwildfires",
        "tk": None,
    },
    "Canterbury": {
        "fb": "https://www.facebook.com/CanterburyRugbyClub",
        "ig": "https://www.instagram.com/canterburyrugbyclub",
        "tk": None,
    },
}


def clean_url(url: str) -> str:
    url = url.split("?")[0].strip()
    if url.endswith("/"):
        url = url[:-1]
    return url


def fetch_html(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="ignore")
            return html
    except Exception as e:
        logger.debug(f"Failed to fetch website {url}: {e}")
        return ""


def validate_url(url: str) -> bool:
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as response:
            code = response.getcode()
            return 200 <= code < 400
    except urllib.error.HTTPError as e:
        # Bot protection often returns 403, 401, 999 etc.
        # However, 404 explicitly means the profile does not exist.
        if e.code in [401, 403, 999]:
            return True
        if e.code == 404:
            return False
        return True  # Treat other errors as soft pass
    except Exception as e:
        logger.debug(f"DNS or connection error for {url}: {e}")
        return False


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def get_candidates(club_name: str):
    slug = slugify(club_name)
    base_slug = (
        slug.replace("rugbyclub", "")
        .replace("rugby", "")
        .replace("oldboys", "")
        .replace("rfc", "")
    )

    fb_candidates = [
        f"https://www.facebook.com/{slug}rugby",
        f"https://www.facebook.com/{slug}rugbyclub",
        f"https://www.facebook.com/{slug}",
        f"https://www.facebook.com/{base_slug}rugby",
        f"https://www.facebook.com/{base_slug}rugbyclub",
        f"https://www.facebook.com/{base_slug}",
    ]
    ig_candidates = [
        f"https://www.instagram.com/{slug}rugby",
        f"https://www.instagram.com/{slug}rugbyclub",
        f"https://www.instagram.com/{slug}",
        f"https://www.instagram.com/{base_slug}rugby",
        f"https://www.instagram.com/{base_slug}rugbyclub",
        f"https://www.instagram.com/{base_slug}",
    ]
    tk_candidates = [
        f"https://www.tiktok.com/@{slug}rugby",
        f"https://www.tiktok.com/@{slug}",
        f"https://www.tiktok.com/@{base_slug}rugby",
    ]

    for key, ovr in CLUB_OVERRIDES.items():
        if key.lower() in club_name.lower():
            if "fb" in ovr:
                if ovr["fb"] is None:
                    fb_candidates = []
                else:
                    fb_candidates.insert(0, ovr["fb"])
            if "ig" in ovr:
                if ovr["ig"] is None:
                    ig_candidates = []
                else:
                    ig_candidates.insert(0, ovr["ig"])
            if "tk" in ovr:
                if ovr["tk"] is None:
                    tk_candidates = []
                else:
                    tk_candidates.insert(0, ovr["tk"])

    return fb_candidates, ig_candidates, tk_candidates


def extract_socials_from_html(html: str):
    fb = None
    ig = None
    tk = None

    fb_match = re.search(
        r'href=["\'](https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_\.\-]+)["\']', html
    )
    if fb_match:
        fb = clean_url(fb_match.group(1))

    ig_match = re.search(
        r'href=["\'](https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_\.\-]+)["\']', html
    )
    if ig_match:
        ig = clean_url(ig_match.group(1))

    tk_match = re.search(
        r'href=["\'](https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_\.\-]+)["\']', html
    )
    if tk_match:
        tk = clean_url(tk_match.group(1))

    return fb, ig, tk


def process_club(club: dict) -> dict:
    name = club.get("name")

    # Apply website overrides if defined
    for key, ovr in CLUB_OVERRIDES.items():
        if key.lower() in name.lower() and "web" in ovr:
            club["website_url"] = ovr["web"]

    website = club.get("website_url")
    logger.info(f"Processing social links for: {name}")

    fb_url, ig_url, tk_url = None, None, None

    # Step 1: Website-First Extraction
    if website:
        logger.info(f"Crawling website for {name}: {website}")
        html = fetch_html(website)
        if html:
            fb_url, ig_url, tk_url = extract_socials_from_html(html)

    # Step 2: Validate website-extracted URLs. If invalid, discard.
    if fb_url and not validate_url(fb_url):
        logger.info(f"Discarding invalid website FB link: {fb_url}")
        fb_url = None
    if ig_url and not validate_url(ig_url):
        logger.info(f"Discarding invalid website IG link: {ig_url}")
        ig_url = None
    if tk_url and not validate_url(tk_url):
        logger.info(f"Discarding invalid website TK link: {tk_url}")
        tk_url = None

    # Step 3: Fallback & Candidate Validation
    fb_candidates, ig_candidates, tk_candidates = get_candidates(name)

    if not fb_url:
        for cand in fb_candidates:
            if validate_url(cand):
                fb_url = cand
                logger.info(f"Found validated fallback FB for {name}: {fb_url}")
                break

    if not ig_url:
        for cand in ig_candidates:
            if validate_url(cand):
                ig_url = cand
                logger.info(f"Found validated fallback IG for {name}: {ig_url}")
                break

    if not tk_url:
        for cand in tk_candidates:
            if validate_url(cand):
                tk_url = cand
                logger.info(f"Found validated fallback TK for {name}: {tk_url}")
                break

    # Save to club dict
    club["facebook_url"] = fb_url
    club["instagram_url"] = ig_url
    club["tiktok_url"] = tk_url

    # Apply absolute manual overrides to guarantee precision
    for key, ovr in CLUB_OVERRIDES.items():
        if key.lower() in name.lower():
            if "fb" in ovr:
                club["facebook_url"] = ovr["fb"]
            if "ig" in ovr:
                club["instagram_url"] = ovr["ig"]
            if "tk" in ovr:
                club["tiktok_url"] = ovr["tk"]

    return club


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "club_scraped_data.json")

    if not os.path.exists(json_path):
        logger.error(f"JSON data not found at {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        clubs = json.load(f)

    logger.info(f"Enriching social media links for {len(clubs)} clubs...")

    enriched_clubs = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_club, club): club for club in clubs}
        for future in as_completed(futures):
            enriched_clubs.append(future.result())

    # Sort back by name to keep ordering consistent
    enriched_clubs.sort(key=lambda c: c.get("name", ""))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(enriched_clubs, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Successfully enriched and saved socials for {len(enriched_clubs)} clubs."
    )


if __name__ == "__main__":
    main()
