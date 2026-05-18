import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "club_scraped_data.json")
out_path = os.path.join(script_dir, "socials_table.md")

with open(json_path, "r", encoding="utf-8") as f:
    clubs = json.load(f)

lines = []
lines.append(f"| Name | Website | Facebook | Instagram | TikTok |")
lines.append(f"| --- | --- | --- | --- | --- |")
for club in clubs:
    name = club.get("name")
    web = club.get("website_url", "")
    fb = club.get("facebook_url", "")
    ig = club.get("instagram_url", "")
    tk = club.get("tiktok_url", "")
    lines.append(f"| {name} | {web} | {fb} | {ig} | {tk} |")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Saved to socials_table.md")
