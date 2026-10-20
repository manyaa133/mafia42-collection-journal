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

# Number / contest / keyword aliases
KEYWORD_MAP = {
    "1st": "contest1", "2nd": "contest2", "3rd": "contest3", "4th": "contest4",
    "5th": "contest5", "6th": "contest6", "7th": "contest7", "8th": "contest8",
    "9th": "contest9", "10th": "contest10", "11th": "contest11", "12th": "contest12",
    "jackpot": "42jackpot", "pass": "mafiapass", "mpass": "mafiapass",
    "summer": "summer", "beach": "summer", "diver": "summer",
    "christmas": "christmas", "xmas": "christmas", "santa": "christmas",
    "fullmoon": "fullmoon", "full moon": "fullmoon",
    "bloodmoon": "bloodmoon", "red moon": "bloodmoon",
    "noir": "noir", "band": "band", "idol": "idol",
    "fairytale": "fairytale", "fairy tale": "fairytale",
    "school": "school", "high school": "school",
    "western": "western", "cowboy": "western",
    "champion": "champion", "winner": "champion",
    "mansion": "mansion", "mansion2019": "mansion",
    "birth": "birth", "birthday": "birth",
    "darktrump": "darktrump", "trump": "darktrump",
    "king": "darktrump", "queen": "darktrump", "jack": "darktrump", "ace": "darktrump", "heart": "darktrump", "clover": "darktrump", "spade": "darktrump", "diamond": "darktrump",
    "fourbeasts": "fourbeasts", "whitetiger": "fourbeasts", "tiger": "fourbeasts", "dragon": "fourbeasts", "phoenix": "fourbeasts", "turtle": "fourbeasts",
    "monster": "monster", "halloween": "monster", "vampire": "monster", "zombie": "monster",
    "detective": "detective", "police": "police", "cop": "police",
    "moorim": "moorim", "martial": "moorim",
    "space": "space", "astronaut": "space",
    "steampunk": "steampunk", "cyberpunk": "cyberpunk",
    "retro": "retro", "classic": "default", "default": "default", "original": "default"
}

def clean_str(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def find_best_subfolders(char_folder, skin_name):
    char_path = os.path.join(ASSETS_BASE_DIR, char_folder)
    if not os.path.exists(char_path):
        return []
    
    subfolders = [d for d in os.listdir(char_path) if os.path.isdir(os.path.join(char_path, d)) and d not in ('ar', 'en', 'ja', 'ko', 'zh_tw')]
    if not subfolders:
        return []

    norm_name = clean_str(skin_name)
    scored = []
    
    for sub in subfolders:
        norm_sub = clean_str(sub)
        score = 0
        if norm_sub in norm_name:
            score += len(norm_sub) * 3
        # Check keyword map
        for kw, target_sub in KEYWORD_MAP.items():
            if kw in norm_name.lower() and (target_sub in sub.lower() or sub.lower() in target_sub):
                score += 15
        if score > 0:
            scored.append((score, sub))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        return [s[1] for s in scored]
    # Fallback to default or all subfolders if needed
    return ["default"] if "default" in subfolders else subfolders[:2]

def run():
    decisions = json.load(open("database/image_review_decisions.json", encoding="utf-8")).get("decisions", {})
    proposals_file_path = "database/proposed_image_replacements.json"
    existing_proposals = json.load(open(proposals_file_path, encoding="utf-8"))
    
    conn = sqlite3.connect("mafia42.db")
    c = conn.cursor()
    skins = c.execute("SELECT id, name, character, image, logo_image FROM catalogue_items WHERE category='skins'").fetchall()
    
    new_skin_proposals = []
    with_candidates = 0

    for sid, sname, schar, simg, slogo in skins:
        cfolder = CHAR_FOLDER_MAP.get(schar.lower().strip(), "none")
        char_path = os.path.join(ASSETS_BASE_DIR, cfolder)
        
        # Rejected URLs for THIS specific skin ID
        rejected_urls = set()
        decision = decisions.get(sid)
        if decision and decision.get("action") == "rejected":
            if decision.get("proposed_url"): rejected_urls.add(decision.get("proposed_url"))
            if decision.get("proposed_logo_url"): rejected_urls.add(decision.get("proposed_logo_url"))

        candidate_subfolders = find_best_subfolders(cfolder, sname)
        
        candidates = []
        best_art_url = None
        best_art_repo = None
        best_logo_url = None
        best_logo_repo = None

        for sub in candidate_subfolders:
            sub_path = os.path.join(char_path, sub)
            if not os.path.exists(sub_path):
                continue
            files = os.listdir(sub_path)
            
            portrait = next((f for f in files if f.startswith("jobclear_") and f.endswith(".webp")), None)
            popup = next((f for f in files if f.startswith("jobpopup_") and f.endswith(".webp")), None)
            cover = next((f for f in files if f.startswith("jobcover_") and f.endswith(".webp")), None)
            thumb = next((f for f in files if f.startswith("jobthumb_") and f.endswith(".webp")), None)

            # Add portrait
            if portrait:
                repo_p = f"assets/character/{cfolder}/{sub}/{portrait}"
                url = f"{RAW_GITHUB_BASE}/{cfolder}/{sub}/{portrait}"
                if url not in rejected_urls and not any(c['url'] == url for c in candidates):
                    cand = {"label": f"Artwork - Full Portrait ({sub})", "type": "artwork", "repo_path": repo_p, "url": url}
                    candidates.append(cand)
                    if not best_art_url:
                        best_art_url = url
                        best_art_repo = repo_p

            # Add popup
            if popup:
                repo_p = f"assets/character/{cfolder}/{sub}/{popup}"
                url = f"{RAW_GITHUB_BASE}/{cfolder}/{sub}/{popup}"
                if url not in rejected_urls and not any(c['url'] == url for c in candidates):
                    cand = {"label": f"Artwork - Popup Art ({sub})", "type": "artwork", "repo_path": repo_p, "url": url}
                    candidates.append(cand)
                    if not best_art_url:
                        best_art_url = url
                        best_art_repo = repo_p

            # Add cover if portrait/popup not available or as extra alternative
            if cover:
                repo_p = f"assets/character/{cfolder}/{sub}/{cover}"
                url = f"{RAW_GITHUB_BASE}/{cfolder}/{sub}/{cover}"
                if url not in rejected_urls and not any(c['url'] == url for c in candidates):
                    cand = {"label": f"Artwork - Card Cover ({sub})", "type": "artwork", "repo_path": repo_p, "url": url}
                    candidates.append(cand)
                    if not best_art_url:
                        best_art_url = url
                        best_art_repo = repo_p

            # Add logo
            if thumb:
                repo_p = f"assets/character/{cfolder}/{sub}/{thumb}"
                url = f"{RAW_GITHUB_BASE}/{cfolder}/{sub}/{thumb}"
                if url not in rejected_urls and not any(c['url'] == url for c in candidates):
                    cand = {"label": f"Logo - Square Badge ({sub})", "type": "logo", "repo_path": repo_p, "url": url}
                    candidates.append(cand)
                    if not best_logo_url:
                        best_logo_url = url
                        best_logo_repo = repo_p

        if candidates:
            with_candidates += 1

        new_skin_proposals.append({
            "id": sid,
            "name": sname,
            "category": "skins",
            "character": schar,
            "current_image": simg,
            "current_logo": slogo,
            "proposed_repo_path": best_art_repo or (f"assets/character/{cfolder}/default/jobpopup_{cfolder}_default.webp" if f"assets/character/{cfolder}/default/jobpopup_{cfolder}_default.webp" not in rejected_urls else ""),
            "proposed_url": best_art_url or (f"{RAW_GITHUB_BASE}/{cfolder}/default/jobpopup_{cfolder}_default.webp" if f"{RAW_GITHUB_BASE}/{cfolder}/default/jobpopup_{cfolder}_default.webp" not in rejected_urls else ""),
            "proposed_logo_repo_path": best_logo_repo or (f"assets/character/{cfolder}/default/jobthumb_{cfolder}_default.webp" if f"assets/character/{cfolder}/default/jobthumb_{cfolder}_default.webp" not in rejected_urls else ""),
            "proposed_logo_url": best_logo_url or (f"{RAW_GITHUB_BASE}/{cfolder}/default/jobthumb_{cfolder}_default.webp" if f"{RAW_GITHUB_BASE}/{cfolder}/default/jobthumb_{cfolder}_default.webp" not in rejected_urls else ""),
            "candidates": candidates
        })

    print(f"Skins with non-rejected candidates: {with_candidates} / {len(skins)}")
    existing_proposals["skins"] = new_skin_proposals
    
    with open(proposals_file_path, "w", encoding="utf-8") as f:
        json.dump(existing_proposals, f, indent=2, ensure_ascii=False)
    print("Successfully updated database/proposed_image_replacements.json!")

if __name__ == "__main__":
    run()

