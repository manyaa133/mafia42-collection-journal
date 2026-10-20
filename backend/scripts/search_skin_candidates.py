import os
import json
import sqlite3
import re

ASSETS_BASE_DIR = r"C:\Users\Manya\Desktop\mafia42\Assets\assets\character"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com/m42garine-source/Assets/main/assets/character"

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

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

decisions = json.load(open("database/image_review_decisions.json", encoding="utf-8")).get("decisions", {})

conn = sqlite3.connect("mafia42.db")
c = conn.cursor()
skins = c.execute("SELECT id, name, character, image, logo_image FROM catalogue_items WHERE category='skins'").fetchall()

print(f"Total skins to check: {len(skins)}")

# For each skin, find candidate folders and files
skin_proposals = []
matched_count = 0

for sid, sname, schar, simg, slogo in skins:
    cfolder = CHAR_FOLDER_MAP.get(schar.lower().strip(), "none")
    char_path = os.path.join(ASSETS_BASE_DIR, cfolder)
    
    # Collect rejected URLs for THIS specific skin ID
    rejected_urls = set()
    decision = decisions.get(sid)
    if decision and decision.get("action") == "rejected":
        if decision.get("proposed_url"): rejected_urls.add(decision.get("proposed_url"))
        if decision.get("proposed_logo_url"): rejected_urls.add(decision.get("proposed_logo_url"))
    
    subfolders = []
    if os.path.exists(char_path):
        subfolders = [d for d in os.listdir(char_path) if os.path.isdir(os.path.join(char_path, d)) and d not in ('ar', 'en', 'ja', 'ko', 'zh_tw')]

    norm_sname = normalize(sname)
    # Remove character name from skin name if present
    norm_char = normalize(schar)
    skin_only_name = norm_sname.replace(norm_char, "")

    best_folder = None
    best_score = 0
    
    for sub in subfolders:
        norm_sub = normalize(sub)
        # Check if sub is in skin_only_name or vice versa
        if norm_sub and (norm_sub in skin_only_name or skin_only_name in norm_sub):
            score = len(norm_sub)
            if score > best_score:
                best_score = score
                best_folder = sub

    candidates = []
    if best_folder:
        folder_path = os.path.join(char_path, best_folder)
        files = os.listdir(folder_path)
        
        # Look for jobclear (portrait), jobpopup (popup artwork), jobcover (cover), jobthumb (logo)
        portrait_file = next((f for f in files if f.startswith("jobclear_") and f.endswith(".webp")), None)
        popup_file = next((f for f in files if f.startswith("jobpopup_") and f.endswith(".webp")), None)
        cover_file = next((f for f in files if f.startswith("jobcover_") and f.endswith(".webp")), None)
        thumb_file = next((f for f in files if f.startswith("jobthumb_") and f.endswith(".webp")), None)
        
        # Add portrait artwork candidate
        main_art_file = portrait_file or popup_file or cover_file
        if main_art_file:
            repo_path = f"assets/character/{cfolder}/{best_folder}/{main_art_file}"
            url = f"{RAW_GITHUB_BASE}/{cfolder}/{best_folder}/{main_art_file}"
            if url not in rejected_urls:
                candidates.append({
                    "label": f"Main Artwork ({'Portrait' if 'jobclear' in main_art_file else 'Popup' if 'jobpopup' in main_art_file else 'Cover'})",
                    "type": "artwork",
                    "repo_path": repo_path,
                    "url": url
                })
                
        # If both clear and popup exist and are not rejected, add both!
        if portrait_file and popup_file and portrait_file != main_art_file:
            repo_path = f"assets/character/{cfolder}/{best_folder}/{popup_file}"
            url = f"{RAW_GITHUB_BASE}/{cfolder}/{best_folder}/{popup_file}"
            if url not in rejected_urls:
                candidates.append({
                    "label": "Main Artwork (Popup)",
                    "type": "artwork",
                    "repo_path": repo_path,
                    "url": url
                })
                
        # Add logo candidate
        if thumb_file:
            repo_path = f"assets/character/{cfolder}/{best_folder}/{thumb_file}"
            url = f"{RAW_GITHUB_BASE}/{cfolder}/{best_folder}/{thumb_file}"
            if url not in rejected_urls:
                candidates.append({
                    "label": "Logo (Square Thumbnail)",
                    "type": "logo",
                    "repo_path": repo_path,
                    "url": url
                })

    if candidates:
        matched_count += 1
        
    skin_proposals.append({
        "id": sid,
        "name": sname,
        "character": schar,
        "category": "skins",
        "current_image": simg,
        "current_logo": slogo,
        "matched_folder": best_folder,
        "candidates_count": len(candidates)
    })

print(f"Matched skins with candidates: {matched_count} / {len(skins)}")

