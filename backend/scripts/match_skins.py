import os
import json
import sqlite3
import re

ASSETS_DIR = r"C:\Users\Manya\Desktop\mafia42\Assets\assets\character"

CHAR_FOLDER_MAP = {
    "administrartor": "none",
    "agent": "agent",
    "beastman": "beastman",
    "cabal": "cabal",
    "citizen": "citizen",
    "cop": "police",
    "cult leader": "cultleader",
    "detective": "detective",
    "doctor": "doctor",
    "fanatic": "fanatic",
    "fortuneteller": "fortuneteller",
    "gangster": "gangster",
    "ghoul": "ghoul",
    "godfather": "godfather",
    "hacker": "hacker",
    "hit-man": "hitman",
    "hostess": "madam",
    "hypnotist": "hypnotist",
    "inspector": "inspector",
    "judge": "judge",
    "lover": "couple",
    "mad scientist": "scientist",
    "mafia": "mafia",
    "magician": "magician",
    "martyr": "martyr",
    "mentalist": "mentalist",
    "mercenary": "mercenary",
    "none": "none",
    "nurse": "nurse",
    "paparazzi": "paparazzi",
    "politician": "politician",
    "priest": "priest",
    "prophet": "prophet",
    "psychic": "shaman",
    "reporter": "reporter",
    "soldier": "soldier",
    "spy": "spy",
    "swindler": "swindler",
    "theif": "thief",
    "vigilante": "vigilante",
    "villan": "villain",
    "witch": "witch",
}

# Load rejected decisions to make sure we NEVER propose a rejected candidate for that item
decisions = json.load(open("database/image_review_decisions.json", encoding="utf-8")).get("decisions", {})

conn = sqlite3.connect("mafia42.db")
c = conn.cursor()
skins = c.execute("SELECT id, name, character, image, logo_image FROM catalogue_items WHERE category='skins'").fetchall()

print(f"Total skins in database: {len(skins)}")
matched = []
unmatched = []

for sid, sname, schar, simg, slogo in skins:
    cfolder = CHAR_FOLDER_MAP.get(schar.lower().strip(), "none")
    char_path = os.path.join(ASSETS_DIR, cfolder)
    
    # Check what subfolders exist
    subfolders = []
    if os.path.exists(char_path):
        subfolders = [d for d in os.listdir(char_path) if os.path.isdir(os.path.join(char_path, d))]
        
    rejected_urls = set()
    if sid in decisions and decisions[sid].get("action") == "rejected":
        rej_prop = decisions[sid].get("proposed_url")
        if rej_prop: rejected_urls.add(rej_prop)
        
    matched.append((sid, sname, schar, cfolder, subfolders))

print(f"Processed {len(matched)} skins. Sample:")
for m in matched[:10]:
    print(f"Skin: {m[1]} ({m[2]}) -> folder: {m[3]}, available skin folders in repo: {len(m[4])}")

