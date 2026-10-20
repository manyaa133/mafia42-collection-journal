import os
import json
import sqlite3
import hashlib
from PIL import Image

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ASSETS_DIR = r"C:\Users\Manya\Desktop\mafia42\Assets"
RAW_BASE_URL = "https://raw.githubusercontent.com/m42garine-source/Assets/main/"

BATCH_STATE_PATH = os.path.join(WORKSPACE_DIR, "database", "frame_batch_state.json")
PROPOSALS_PATH = os.path.join(WORKSPACE_DIR, "database", "proposed_image_replacements.json")
DECISIONS_PATH = os.path.join(WORKSPACE_DIR, "database", "image_review_decisions.json")
DB_PATH = os.path.join(WORKSPACE_DIR, "mafia42.db")

def get_file_hash(rel_path):
    full_p = os.path.join(REPO_ASSETS_DIR, rel_path.replace('/', os.sep))
    if os.path.exists(full_p):
        with open(full_p, 'rb') as fp:
            return hashlib.sha256(fp.read()).hexdigest()
    return None

def url_to_rel(url):
    if url and url.startswith(RAW_BASE_URL):
        return url.replace(RAW_BASE_URL, '')
    return None

def load_assigned_assets():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, image FROM catalogue_items WHERE category='frames'")
    db_rows = c.fetchall()
    conn.close()

    dec_data = {"decisions": {}, "rejected_history": {}}
    if os.path.exists(DECISIONS_PATH):
        with open(DECISIONS_PATH, 'r', encoding='utf-8') as f:
            dec_data = json.load(f)
    decs = dec_data.get('decisions', {})

    used_urls = set()
    used_hashes = set()
    used_filenames = set()
    approved_fids = set()
    pending_frames = []

    for fid, name, img in db_rows:
        dec = decs.get(fid)
        if dec and dec.get('action') == 'approved':
            approved_fids.add(fid)
            p_url = dec.get('proposed_url')
            if p_url:
                used_urls.add(p_url)
                used_filenames.add(os.path.basename(p_url))
                rel = url_to_rel(p_url)
                if rel:
                    h = get_file_hash(rel)
                    if h: used_hashes.add(h)
            if img and img.startswith('http'):
                used_urls.add(img)
                used_filenames.add(os.path.basename(img))
                rel = url_to_rel(img)
                if rel:
                    h = get_file_hash(rel)
                    if h: used_hashes.add(h)
        else:
            pending_frames.append({
                'id': fid,
                'name': name,
                'current_image': img
            })

    rejected_urls = set()
    rejected_hashes = set()
    rejected_filenames = set()
    rej_hist = dec_data.get('rejected_history', {})
    for item_id, urls in rej_hist.items():
        for u in urls:
            if u and 'frame' in u.lower():
                rejected_urls.add(u)
                rejected_filenames.add(os.path.basename(u).lower())
                rel = url_to_rel(u)
                if rel:
                    h = get_file_hash(rel)
                    if h: rejected_hashes.add(h)

    return approved_fids, pending_frames, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames

def load_batch_state():
    try:
        import backend.scripts.manage_skin_batches as msb
        import importlib
        importlib.reload(msb)
        msb.init_or_get_batch_1("skin_main", n=20)
    except Exception as e:
        import traceback
        traceback.print_exc()

    if os.path.exists(BATCH_STATE_PATH):
        try:
            with open(BATCH_STATE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_batch_number": 0,
        "current_batch": [],
        "presented_history_hashes": [],
        "presented_history_urls": [],
        "batch_history": []
    }

def save_batch_state(state):
    with open(BATCH_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def scan_all_frame_assets():
    frame_dir = os.path.join(REPO_ASSETS_DIR, "assets", "item", "frame")
    general_dir = os.path.join(REPO_ASSETS_DIR, "assets", "item", "general")
    playerinfo_dir = os.path.join(REPO_ASSETS_DIR, "assets", "playerinfo")

    all_assets = []
    def collect(folder, cat_type):
        if not os.path.exists(folder):
            return
        for root, dirs, files in os.walk(folder):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.png', '.webp', '.jpg', '.jpeg'):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, REPO_ASSETS_DIR).replace('\\', '/')
                    if 'frame' in rel_p.lower():
                        all_assets.append((full_p, rel_p, f, cat_type))

    collect(frame_dir, "item_frame")
    collect(general_dir, "general_frame")
    collect(playerinfo_dir, "playerinfo_frame")
    return all_assets

def get_next_candidates(n=5, exclude_hashes=None, exclude_urls=None):
    if exclude_hashes is None: exclude_hashes = set()
    if exclude_urls is None: exclude_urls = set()

    approved_fids, pending_frames, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames = load_assigned_assets()
    all_excluded_hashes = set(exclude_hashes) | used_hashes | rejected_hashes
    all_excluded_urls = set(exclude_urls) | used_urls | rejected_urls

    all_assets = scan_all_frame_assets()
    candidates = []
    seen_hashes = set()

    # Prioritize assets/item/frame/ first, then item/general, then playerinfo
    for full_p, rel_p, fname, cat_type in all_assets:
        try:
            with open(full_p, 'rb') as fp:
                h = hashlib.sha256(fp.read()).hexdigest()
            url = RAW_BASE_URL + rel_p

            if h in all_excluded_hashes or url in all_excluded_urls or h in seen_hashes:
                continue

            # Also check if filename is already used or rejected
            if fname in used_filenames or fname.lower() in rejected_filenames:
                continue

            with Image.open(full_p) as im:
                w, h_dim = im.size

            seen_hashes.add(h)
            candidates.append({
                'label': f"Candidate {len(candidates) + 1}",
                'type': cat_type,
                'repo_path': rel_p,
                'filename': fname,
                'url': url,
                'hash': h,
                'dimensions': f"{w} × {h_dim}",
                'is_unused': True,
                'already_used_by': None,
                'reason': f"Shared batch frame asset ({w} × {h_dim})"
            })

            if len(candidates) == n:
                break
        except Exception:
            pass

    return candidates

def apply_shared_batch_to_pending(candidates, batch_num):
    approved_fids, pending_frames, *rest = load_assigned_assets()

    with open(PROPOSALS_PATH, 'r', encoding='utf-8') as f:
        proposals_data = json.load(f)

    frame_proposals = proposals_data.get('frames', [])
    updated_proposals = []

    pending_map = {pf['id']: pf for pf in pending_frames}

    for prop in frame_proposals:
        fid = prop['id']
        if fid in pending_map:
            pf = pending_map[fid]
            updated_proposals.append({
                'id': fid,
                'name': pf['name'],
                'category': 'frames',
                'current_image': pf['current_image'],
                'proposed_url': candidates[0]['url'] if candidates else None,
                'proposed_repo_path': candidates[0]['repo_path'] if candidates else '',
                'candidates': candidates,
                'batch_number': batch_num
            })
        else:
            updated_proposals.append(prop)

    proposals_data['frames'] = updated_proposals

    with open(PROPOSALS_PATH, 'w', encoding='utf-8') as f:
        json.dump(proposals_data, f, indent=2, ensure_ascii=False)

def init_or_get_batch_1(force_reselect=False):
    state = load_batch_state()
    approved_fids, pending_frames, used_urls, used_hashes, used_filenames, rejected_urls, rejected_hashes, rejected_filenames = load_assigned_assets()

    # Check if existing batch 1 has any rejected candidates
    has_rejected = False
    for c in state.get('current_batch', []):
        if c.get('hash') in rejected_hashes or c.get('filename', '').lower() in rejected_filenames:
            has_rejected = True
            break

    if not force_reselect and not has_rejected and state.get('current_batch_number') == 1 and len(state.get('current_batch', [])) == 5:
        print("Batch 1 is already prepared:")
        for c in state['current_batch']:
            print(f"  {c['label']}: {c['filename']} ({c['dimensions']}) -> {c['repo_path']}")
        apply_shared_batch_to_pending(state['current_batch'], 1)
        return state['current_batch']

    # Select 5 genuinely fresh candidates for Batch 1
    cands = get_next_candidates(5)
    state['current_batch_number'] = 1
    state['current_batch'] = cands
    state['presented_history_hashes'] = [c['hash'] for c in cands]
    state['presented_history_urls'] = [c['url'] for c in cands]
    state['batch_history'] = [{
        'batch_number': 1,
        'candidates': cands
    }]
    save_batch_state(state)
    apply_shared_batch_to_pending(cands, 1)

    print(f"Successfully initialized Shared Batch #1 with {len(cands)} candidates:")
    for c in cands:
        print(f"  {c['label']}: {c['filename']} ({c['dimensions']}) -> {c['repo_path']}")
    return cands

def advance_to_next_batch():
    state = load_batch_state()
    current_num = state.get('current_batch_number', 0)
    next_num = current_num + 1

    history_hashes = set(state.get('presented_history_hashes', []))
    history_urls = set(state.get('presented_history_urls', []))

    # Add current batch to history if not already there
    for c in state.get('current_batch', []):
        history_hashes.add(c['hash'])
        history_urls.add(c['url'])

    new_cands = get_next_candidates(5, exclude_hashes=history_hashes, exclude_urls=history_urls)
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
    save_batch_state(state)
    apply_shared_batch_to_pending(new_cands, next_num)

    print(f"Advanced to Shared Batch #{next_num} with {len(new_cands)} candidates:")
    for c in new_cands:
        print(f"  {c['label']}: {c['filename']} ({c['dimensions']}) -> {c['repo_path']}")
    return new_cands

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'next':
        advance_to_next_batch()
    else:
        init_or_get_batch_1()
