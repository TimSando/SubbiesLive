import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "club_scraped_data.json")

with open(json_path, "r", encoding="utf-8") as f:
    clubs = json.load(f)

print(f"| Name | Website | Facebook | Instagram | TikTok |")
print(f"| --- | --- | --- | --- | --- |")
for club in clubs:
    name = club.get("name")
    web = club.get("website_url", "")
    fb = club.get("facebook_url", "")
    ig = club.get("instagram_url", "")
    tk = club.get("tiktok_url", "")
    print(f"| {name} | {web} | {fb} | {ig} | {tk} |")
