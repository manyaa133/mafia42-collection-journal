import os
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Tuple, Set
from PIL import Image

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ASSETS_DIR = r"C:\Users\Manya\Desktop\mafia42\Assets"
RAW_BASE_URL = "https://raw.githubusercontent.com/m42garine-source/Assets/main/"

PROPOSALS_PATH = os.path.join(WORKSPACE_DIR, "database", "proposed_image_replacements.json")
DECISIONS_PATH = os.path.join(WORKSPACE_DIR, "database", "image_review_decisions.json")
SEED_CATALOGUE_PATH = os.path.join(WORKSPACE_DIR, "database", "seed_catalogue.json")
DB_PATH = os.path.join(WORKSPACE_DIR, "mafia42.db")

def get_batch_state_path(mode: str) -> str:
    filename = "skin_main_batch_state.json" if mode == "skin_main" else "skin_logo_batch_state.json"
    return os.path.join(WORKSPACE_DIR, "database", filename)

def get_file_hash(rel_path: str) -> str:
    full_p = os.path.join(REPO_ASSETS_DIR, rel_path.replace('/', os.sep))
    if os.path.exists(full_p):
        with open(full_p, 'rb') as fp:
            return hashlib.sha256(fp.read()).hexdigest()
    return ""

def url_to_rel(url: str) -> str:
    if url and url.startswith(RAW_BASE_URL):
        return url.replace(RAW_BASE_URL, '')
    return ""

def load_assigned_assets(mode: str = "skin_main"):
    """
    Returns:
      approved_ids: set of skin IDs already approved in this mode
      pending_skins: list of pending skin dicts
      used_urls: set of URLs already used across catalogue / approved skins
      used_hashes: set of SHA256 hashes of already assigned skins
      used_filenames: set of filenames of already assigned skins
      rejected_urls: set of URLs rejected for this mode
      rejected_hashes: set of hashes rejected for this mode
      rejected_filenames: set of filenames rejected for this mode
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, character, image, logo_image FROM catalogue_items WHERE category='skins'")
    db_rows = c.fetchall()
    conn.close()

    dec_data = {"decisions": {}, "rejected_history": {}}
    if os.path.exists(DECISIONS_PATH):
        try:
            with open(DECISIONS_PATH, 'r', encoding='utf-8') as f:
                dec_data = json.load(f)
        except Exception:
            pass
    decs = dec_data.get('decisions', {})

    used_urls: Set[str] = set()
    used_hashes: Set[str] = set()
    used_filenames: Set[str] = set()
    approved_ids: Set[str] = set()
    pending_skins = []

    # Also check seed catalogue directly for any assigned images
    seed_skins = []
    if os.path.exists(SEED_CATALOGUE_PATH):
        try:
            with open(SEED_CATALOGUE_PATH, 'r', encoding='utf-8') as sf:
                scat = json.load(sf)
                seed_skins = scat.get('skins', [])
        except Exception:
            pass

    # Collect assigned images from all skins in catalogue
    for s in seed_skins:
        img_url = s.get('image', '')
        logo_url = s.get('logo_image', '')

        target_url = img_url if mode == "skin_main" else logo_url
        if target_url and target_url.startswith('http'):
            used_urls.add(target_url)
            fname = os.path.basename(target_url)
            used_filenames.add(fname)
            used_filenames.add(fname.lower())
            rel = url_to_rel(target_url)
            if rel:
                h = get_file_hash(rel)
                if h: used_hashes.add(h)

    for sid, name, character, img, logo_img in db_rows:
        prop_id = f"{mode}_{sid}"
        dec = decs.get(prop_id)
        target_img = img if mode == "skin_main" else logo_img

        if dec and dec.get('action') == 'approved':
            approved_ids.add(sid)
            p_url = dec.get('proposed_url')
            if p_url:
                used_urls.add(p_url)
                fname = os.path.basename(p_url)
                used_filenames.add(fname)
                used_filenames.add(fname.lower())
                rel = url_to_rel(p_url)
                if rel:
                    h = get_file_hash(rel)
                    if h: used_hashes.add(h)
            if target_img and target_img.startswith('http'):
                used_urls.add(target_img)
                fname = os.path.basename(target_img)
                used_filenames.add(fname)
                used_filenames.add(fname.lower())
                rel = url_to_rel(target_img)
                if rel:
                    h = get_file_hash(rel)
                    if h: used_hashes.add(h)
        else:
            # Check if image in DB is already a valid approved webp from remote repo
            # Only consider approved if explicitly decided or verified
            pending_skins.append({
                'id': prop_id,
                'skin_id': sid,
                'name': f"{name} ({'Main Image' if mode == 'skin_main' else 'Logo'})",
                'skin_name': name,
                'character': character or "None",
                'current_image': target_img or f"/assets/skins/skin_{sid}.jpg"
            })

    rejected_urls: Set[str] = set()
    rejected_hashes: Set[str] = set()
    rejected_filenames: Set[str] = set()
    rej_hist = dec_data.get('rejected_history', {})
    for item_id, urls in rej_hist.items():
        if mode in item_id:
            for u in urls:
                if u:
                    rejected_urls.add(u)
                    fname = os.path.basename(u)
                    rejected_filenames.add(fname.lower())
                    rel = url_to_rel(u)
                    if rel:
                        h = get_file_hash(rel)
                        if h: rejected_hashes.add(h)

    return approved_ids, pending_skins, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames

def load_batch_state(mode: str = "skin_main") -> dict:
    state_path = get_batch_state_path(mode)
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "mode": mode,
        "current_batch_number": 0,
        "current_batch": [],
        "presented_history_hashes": [],
        "presented_history_urls": [],
        "batch_history": []
    }

def save_batch_state(state: dict, mode: str = "skin_main"):
    state_path = get_batch_state_path(mode)
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def scan_all_skin_assets(mode: str = "skin_main"):
    r"""
    Scans repo for eligible skin assets.
    For skin_main:
      - Full-body portrait artworks: jobclear_*, jobstanding_*, jobpopup_*
      - High-resolution (1000 × 1200 preferred)
      - Excludes thumbnails, icons, buttons, small badges (jobthumb_*, jobicon_*, etc.)
    For skin_logo:
      - Small badges / thumbnails: jobthumb_*, jobicon_*
      - Dimensions <= 512 × 512
      - Excludes full artwork (jobclear_*, 1000x1200)
    """
    char_dir = os.path.join(REPO_ASSETS_DIR, "assets", "character")
    all_assets = []

    if not os.path.exists(char_dir):
        return all_assets

    for root, dirs, files in os.walk(char_dir):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext not in ('.webp', '.png', '.jpg', '.jpeg'):
                continue

            fname_lower = f.lower()
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, REPO_ASSETS_DIR).replace('\\', '/')

            # Exclude card default artworks if they are card-specific
            # e.g., assets/character/{role}/default/jobthumb_* or jobpopup_*
            # but allow skin folders e.g. assets/character/{role}/{skin_theme}/
            parts = rel_p.split('/')
            
            # Determine eligibility based on mode
            if mode == "skin_main":
                # Exclude any logos, thumbnails, icons, mini badges, or sprites
                if any(k in fname_lower for k in [
                    'thumb', 'icon', 'small', 'mini', 'badge', 'card', 'btn', 'skill', 'emoji', 'pixel', 'sd_'
                ]):
                    continue

                # Primary target filenames for main artwork
                is_clear = 'jobclear' in fname_lower
                is_standing = 'jobstanding' in fname_lower
                is_popup = 'jobpopup' in fname_lower

                if not (is_clear or is_standing or is_popup):
                    continue

                # Filter out base card default character illustrations
                if 'default' in parts:
                    continue

                all_assets.append((full_p, rel_p, f, is_clear or is_standing))
            else:
                # Mode is skin_logo
                if any(k in fname_lower for k in ['clear', 'standing', 'popup', 'full', 'illustration']):
                    continue
                if any(k in fname_lower for k in ['thumb', 'icon', 'logo']):
                    all_assets.append((full_p, rel_p, f, True))

    return all_assets

def get_next_candidates(mode: str = "skin_main", n: int = 20, exclude_hashes: Set[str] = None, exclude_urls: Set[str] = None) -> List[Dict[str, Any]]:
    if exclude_hashes is None: exclude_hashes = set()
    if exclude_urls is None: exclude_urls = set()

    approved_ids, pending_skins, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames = load_assigned_assets(mode)
    all_excluded_hashes = set(exclude_hashes) | used_hashes | rejected_hashes
    all_excluded_urls = set(exclude_urls) | used_urls | rejected_urls

    raw_assets = scan_all_skin_assets(mode)
    candidates = []
    seen_hashes: Set[str] = set()

    # Sort assets: prioritize 1000x1200 jobclear assets first
    # Sort key: (is_priority desc, filename)
    raw_assets.sort(key=lambda x: (not x[3], x[1]))

    for full_p, rel_p, fname, is_priority in raw_assets:
        try:
            with open(full_p, 'rb') as fp:
                h = hashlib.sha256(fp.read()).hexdigest()
            url = RAW_BASE_URL + rel_p

            if h in all_excluded_hashes or url in all_excluded_urls or h in seen_hashes:
                continue

            if fname in used_filenames or fname.lower() in rejected_filenames:
                continue

            with Image.open(full_p) as im:
                w, h_dim = im.size

            if mode == "skin_main":
                # Ensure it's not an extreme landscape banner
                if w > h_dim * 2.2:
                    # Extreme panorama banner, skip
                    continue
                # Skip tiny images
                if h_dim < 300 or w < 250:
                    continue
            else:
                # Logo mode: ensure it's not a giant full artwork
                if h_dim > 600 or w > 600:
                    continue

            seen_hashes.add(h)
            candidates.append({
                'label': f"Candidate {len(candidates) + 1}",
                'type': "artwork" if mode == "skin_main" else "logo",
                'repo_path': rel_p,
                'filename': fname,
                'url': url,
                'hash': h,
                'dimensions': f"{w} × {h_dim}",
                'is_unused': True,
                'already_used_by': None,
                'reason': f"Distinct unused skin asset ({w} × {h_dim})"
            })

            if len(candidates) == n:
                break
        except Exception:
            pass

    return candidates

def apply_shared_batch_to_pending(candidates: List[Dict[str, Any]], batch_num: int, mode: str = "skin_main"):
    approved_ids, pending_skins, *rest = load_assigned_assets(mode)

    with open(PROPOSALS_PATH, 'r', encoding='utf-8') as f:
        proposals_data = json.load(f)

    category_key = mode  # 'skin_main' or 'skin_logo'
    existing_proposals = proposals_data.get(category_key, [])
    updated_proposals = []

    pending_map = {ps['id']: ps for ps in pending_skins}

    for prop in existing_proposals:
        pid = prop['id']
        if pid in pending_map:
            ps = pending_map[pid]
            updated_proposals.append({
                'id': pid,
                'skin_id': ps['skin_id'],
                'name': ps['name'],
                'category': category_key,
                'character': ps.get('character', prop.get('character', 'None')),
                'current_image': ps['current_image'],
                'proposed_url': candidates[0]['url'] if candidates else None,
                'proposed_repo_path': candidates[0]['repo_path'] if candidates else '',
                'candidates': candidates,
                'batch_number': batch_num
            })
        else:
            updated_proposals.append(prop)

    proposals_data[category_key] = updated_proposals

    with open(PROPOSALS_PATH, 'w', encoding='utf-8') as f:
        json.dump(proposals_data, f, indent=2, ensure_ascii=False)

def init_or_get_batch_1(mode: str = "skin_main", force_reselect: bool = False, n: int = 20) -> List[Dict[str, Any]]:
    state = load_batch_state(mode)
    approved_ids, pending_skins, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames = load_assigned_assets(mode)

    # Check if existing batch 1 has any rejected candidates
    has_rejected = False
    for c in state.get('current_batch', []):
        if c.get('hash') in rejected_hashes or c.get('filename', '').lower() in rejected_filenames:
            has_rejected = True
            break

    if not force_reselect and not has_rejected and state.get('current_batch_number') == 1 and len(state.get('current_batch', [])) == n:
        apply_shared_batch_to_pending(state['current_batch'], 1, mode)
        return state['current_batch']

    # Select n genuinely fresh candidates for Batch 1
    cands = get_next_candidates(mode, n=n)
    state['current_batch_number'] = 1
    state['current_batch'] = cands
    state['presented_history_hashes'] = [c['hash'] for c in cands]
    state['presented_history_urls'] = [c['url'] for c in cands]
    state['batch_history'] = [{
        'batch_number': 1,
        'candidates': cands
    }]
    save_batch_state(state, mode)
    apply_shared_batch_to_pending(cands, 1, mode)
    return cands

def advance_to_next_batch(mode: str = "skin_main", n: int = 20) -> List[Dict[str, Any]]:
    state = load_batch_state(mode)
    current_num = state.get('current_batch_number', 0)
    next_num = current_num + 1

    history_hashes = set(state.get('presented_history_hashes', []))
    history_urls = set(state.get('presented_history_urls', []))

    for c in state.get('current_batch', []):
        history_hashes.add(c['hash'])
        history_urls.add(c['url'])

    new_cands = get_next_candidates(mode, n=n, exclude_hashes=history_hashes, exclude_urls=history_urls)
    for idx, c in enumerate(new_cands, 1):
        c['label'] = f"Candidate {idx}"

    for c in new_cands:
        history_hashes.add(c['hash'])
        history_urls.add(c['url'])

    state['current_batch_number'] = next_num
    state['current_batch'] = new_cands
    state['presented_history_hashes'] = list(history_hashes)
    state['presented_history_urls'] = list(history_urls)
    state['batch_history'].append({
        'batch_number': next_num,
        'candidates': new_cands
    })
    save_batch_state(state, mode)
    apply_shared_batch_to_pending(new_cands, next_num, mode)
    return new_cands

def switch_to_batch(batch_num: int, mode: str = "skin_main") -> List[Dict[str, Any]]:
    state = load_batch_state(mode)
    history = state.get('batch_history', [])
    found = None
    for b in history:
        if b.get('batch_number') == batch_num:
            found = b.get('candidates', [])
            break
    if found is None:
        raise ValueError(f"Batch #{batch_num} not found in history for {mode}")

    state['current_batch_number'] = batch_num
    state['current_batch'] = found
    save_batch_state(state, mode)
    apply_shared_batch_to_pending(found, batch_num, mode)
    return found

if __name__ == '__main__':
    import sys
    mode = "skin_main"
    if "--logo" in sys.argv or "skin_logo" in sys.argv:
        mode = "skin_logo"
    
    if "next" in sys.argv:
        cands = advance_to_next_batch(mode=mode, n=20)
        print(f"Advanced to next batch for {mode} with {len(cands)} candidates.")
        for idx, c in enumerate(cands, 1):
            print(f"  {idx}. {c['filename']} ({c['dimensions']}) -> {c['repo_path']}")
    else:
        force = "--force" in sys.argv
        cands = init_or_get_batch_1(mode=mode, force_reselect=force, n=20)
        print(f"Initialized Batch 1 for {mode} with {len(cands)} candidates.")
        for idx, c in enumerate(cands, 1):
            print(f"  {idx}. {c['filename']} ({c['dimensions']}) -> {c['repo_path']}")

