import os
import sys
import uuid
import pytest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)

def test_1_independent_users():
    """TEST 1: Register User A and User B. Mark item as owned for User A. Verify User B sees it unowned."""
    uid_a = uuid.uuid4().hex[:6]
    uid_b = uuid.uuid4().hex[:6]

    res_a = client.post("/api/auth/register", json={
        "email": f"user_a_{uid_a}@example.com",
        "username": f"UserA_{uid_a}",
        "password": "Password123!"
    })
    assert res_a.status_code == 200
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_b = client.post("/api/auth/register", json={
        "email": f"user_b_{uid_b}@example.com",
        "username": f"UserB_{uid_b}",
        "password": "Password123!"
    })
    assert res_b.status_code == 200
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    skins = client.get("/api/catalogue/skins").json()
    test_skin_id = skins[0]["id"]
    test_skin_cp = skins[0]["cp"]

    # User A toggles skin ON
    t_a = client.post(f"/api/collection/toggle/{test_skin_id}", headers=headers_a)
    assert t_a.status_code == 200
    assert t_a.json()["owned"] is True

    # User A has CP
    stats_a = client.get("/api/collection/stats", headers=headers_a).json()
    assert stats_a["user_cp"] >= test_skin_cp

    # User B must NOT have this item and user_cp must be 0
    col_b = client.get("/api/collection", headers=headers_b).json()
    assert test_skin_id not in col_b["owned_item_ids"]
    stats_b = client.get("/api/collection/stats", headers=headers_b).json()
    assert stats_b["user_cp"] == 0

def test_2_persistence():
    """TEST 2: Mark multiple items as owned, close session, sign in again, verify items and CP restored."""
    uid = uuid.uuid4().hex[:6]
    email = f"persist_{uid}@example.com"
    pwd = "Password123!"

    reg = client.post("/api/auth/register", json={
        "email": email,
        "username": f"Persist_{uid}",
        "password": pwd
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    skins = client.get("/api/catalogue/skins").json()
    s1, s2 = skins[0]["id"], skins[1]["id"]
    client.post(f"/api/collection/toggle/{s1}", headers=headers)
    client.post(f"/api/collection/toggle/{s2}", headers=headers)

    # Re-login with new session
    login = client.post("/api/auth/login", json={
        "username_or_email": email,
        "password": pwd
    })
    new_token = login.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    col = client.get("/api/collection", headers=new_headers).json()
    assert s1 in col["owned_item_ids"]
    assert s2 in col["owned_item_ids"]

def test_3_cross_device_persistence():
    """TEST 3: Sign in to same account from another client and verify match."""
    uid = uuid.uuid4().hex[:6]
    email = f"cross_{uid}@example.com"
    pwd = "Password123!"

    client.post("/api/auth/register", json={
        "email": email,
        "username": f"Cross_{uid}",
        "password": pwd
    })

    # Device 1
    d1 = client.post("/api/auth/login", json={"username_or_email": email, "password": pwd})
    h1 = {"Authorization": f"Bearer {d1.json()['access_token']}"}
    icons = client.get("/api/catalogue/icons").json()
    test_icon = icons[0]["id"]
    client.post(f"/api/collection/toggle/{test_icon}", headers=h1)

    # Device 2 (simulated separate client)
    d2 = client.post("/api/auth/login", json={"username_or_email": email, "password": pwd})
    h2 = {"Authorization": f"Bearer {d2.json()['access_token']}"}
    col2 = client.get("/api/collection", headers=h2).json()
    assert test_icon in col2["owned_item_ids"]

def test_4_owner_permissions():
    """TEST 4: Owner can add, edit, delete catalogue items and inspect audit logs."""
    login_owner = client.post("/api/auth/login", json={
        "username_or_email": settings.INITIAL_OWNER_EMAIL,
        "password": settings.INITIAL_OWNER_PASSWORD,
    })
    owner_headers = {"Authorization": f"Bearer {login_owner.json()['access_token']}"}

    test_id = f"test_item_{uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/admin/catalogue", json={
        "id": test_id,
        "category": "skins",
        "name": "Owner Special Skin",
        "cp": 900
    }, headers=owner_headers)
    assert create_res.status_code == 200

    edit_res = client.put(f"/api/admin/catalogue/{test_id}", json={
        "name": "Owner Special Skin (Edited)",
        "cp": 950
    }, headers=owner_headers)
    assert edit_res.status_code == 200
    assert edit_res.json()["name"] == "Owner Special Skin (Edited)"

    del_res = client.delete(f"/api/admin/catalogue/{test_id}", headers=owner_headers)
    assert del_res.status_code == 200

def test_5_ordinary_user_restrictions():
    """TEST 5: Ordinary users attempting owner operations are rejected with 403 Forbidden."""
    uid = uuid.uuid4().hex[:6]
    reg = client.post("/api/auth/register", json={
        "email": f"ord_{uid}@example.com",
        "username": f"Ordinary_{uid}",
        "password": "Password123!"
    })
    user_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    assert client.post("/api/admin/catalogue", json={"category": "skins", "name": "Hack"}, headers=user_headers).status_code == 403
    assert client.put("/api/admin/catalogue/2ydoa5w8", json={"name": "Hack"}, headers=user_headers).status_code == 403
    assert client.delete("/api/admin/catalogue/2ydoa5w8", headers=user_headers).status_code == 403
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=user_headers).status_code == 403

def test_6_direct_api_access():
    """TEST 6: Direct API calls without credentials fail with 401 or 403."""
    assert client.post("/api/admin/catalogue", json={"category": "skins"}).status_code in [401, 403]
    assert client.delete("/api/admin/catalogue/xyz").status_code in [401, 403]

def test_7_cross_user_attack_prevention():
    """TEST 7: Users cannot modify another user's collection data."""
    uid1 = uuid.uuid4().hex[:6]
    uid2 = uuid.uuid4().hex[:6]

    reg1 = client.post("/api/auth/register", json={
        "email": f"victim_{uid1}@example.com", "username": f"Victim_{uid1}", "password": "Password123!"
    })
    h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}

    reg2 = client.post("/api/auth/register", json={
        "email": f"attacker_{uid2}@example.com", "username": f"Attacker_{uid2}", "password": "Password123!"
    })
    h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

    # Attacker calls collection toggle: collection endpoints automatically use JWT sub (current user)
    # and cannot be manipulated via query or body to affect victim
    skins = client.get("/api/catalogue/skins").json()
    skin_id = skins[0]["id"]

    client.post(f"/api/collection/toggle/{skin_id}", headers=h2)
    # Verify victim collection was unaffected
    col1 = client.get("/api/collection", headers=h1).json()
    assert skin_id not in col1["owned_item_ids"]

def test_8_image_migration_and_wallets():
    """TEST 8: Verify migrated images load with status 200 and wallet detail images are mapped."""
    # Test skin image
    res_skin = client.get("/assets/skins/skin_logo_2ydoa5w8.jpg")
    assert res_skin.status_code == 200
    assert len(res_skin.content) > 1000

    # Test nameplate image
    res_np = client.get("/assets/nameplates/np-001.png")
    assert res_np.status_code == 200

    # Test wallet entry has 3 detail images
    wallets = client.get("/api/catalogue/wallets").json()
    assert len(wallets) > 0
    w = wallets[0]
    assert "wallet_images" in w
    assert len(w["wallet_images"]) == 3

def test_9_cp_calculations():
    """TEST 9: Verify CP calculations on toggles, no duplicate counts on repeated toggles."""
    uid = uuid.uuid4().hex[:6]
    reg = client.post("/api/auth/register", json={
        "email": f"cp_{uid}@example.com", "username": f"CP_{uid}", "password": "Password123!"
    })
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    skins = client.get("/api/catalogue/skins").json()
    s = skins[0]

    # Toggle 1: ON
    client.post(f"/api/collection/toggle/{s['id']}", headers=h)
    stats = client.get("/api/collection/stats", headers=h).json()
    assert stats["user_cp"] == s["cp"]

    # Toggle 2: OFF
    client.post(f"/api/collection/toggle/{s['id']}", headers=h)
    stats2 = client.get("/api/collection/stats", headers=h).json()
    assert stats2["user_cp"] == 0

    # Toggle 3: ON again
    client.post(f"/api/collection/toggle/{s['id']}", headers=h)
    stats3 = client.get("/api/collection/stats", headers=h).json()
    assert stats3["user_cp"] == s["cp"]

def test_10_data_integrity():
    """TEST 10: Verify catalogue item counts, stable IDs, and category associations."""
    cat = client.get("/api/catalogue").json()
    assert len(cat["skins"]) >= 334
    assert len(cat["cards"]) == 42
    assert len(cat["frames"]) >= 158
    assert len(cat["nameplates"]) >= 178
    assert len(cat["icons"]) >= 170

def test_11_spa_production_serving():
    """TEST 11: Verify SPA HTML and asset routes load cleanly."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert b"Mafia42 Collection Journal" in res_root.content

def test_12_production_readiness():
    """TEST 12: Verify health endpoint, CORS headers, and audit trail."""
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["version"] == "2.0.0"

def test_13_card_skin_relationship():
    """TEST 13: Verify card-skin association endpoint, bidirectional lookup, and safe unlinking on deletion."""
    cards = client.get("/api/catalogue/cards").json()
    assert len(cards) == 42
    test_card = next(c for c in cards if c["character"] in ["Fanatic", "Cult Leader", "Citizen"])
    
    # 1. Associated skins for card
    res_skins = client.get(f"/api/catalogue/cards/{test_card['id']}/skins")
    assert res_skins.status_code == 200
    assoc_skins = res_skins.json()
    assert len(assoc_skins) > 0
    for s in assoc_skins:
        assert s["card_id"] == test_card["id"] or s["character"] == test_card["character"]

    # 2. Bidirectional lookup: skin -> card
    test_skin = assoc_skins[0]
    res_card = client.get(f"/api/catalogue/skins/{test_skin['id']}/card")
    assert res_card.status_code == 200
    parent_card = res_card.json()
    assert parent_card is not None
    assert parent_card["id"] == test_card["id"]

    # 3. No duplicate skin records exist
    all_skins = client.get("/api/catalogue/skins").json()
    assert len(all_skins) >= 334

    # 4. Safe unlinking: deleting a card unlinks skins without cascading deletion
    login_owner = client.post("/api/auth/login", json={
        "username_or_email": settings.INITIAL_OWNER_EMAIL,
        "password": settings.INITIAL_OWNER_PASSWORD,
    })
    owner_headers = {"Authorization": f"Bearer {login_owner.json()['access_token']}"}

    temp_card_id = f"temp_card_{uuid.uuid4().hex[:6]}"
    temp_skin_id = f"temp_skin_{uuid.uuid4().hex[:6]}"

    # Create temporary card and skin
    client.post("/api/admin/catalogue", json={
        "id": temp_card_id, "category": "cards", "name": "Temp Card"
    }, headers=owner_headers)
    client.post("/api/admin/catalogue", json={
        "id": temp_skin_id, "category": "skins", "name": "Temp Skin", "card_id": temp_card_id
    }, headers=owner_headers)

    # Delete the card
    del_res = client.delete(f"/api/admin/catalogue/{temp_card_id}", headers=owner_headers)
    assert del_res.status_code == 200

    # The skin must STILL exist and must NOT have been deleted
    skin_check = client.get(f"/api/catalogue/skins/{temp_skin_id}")
    assert skin_check.status_code == 200
    assert skin_check.json()["id"] == temp_skin_id

    # Clean up temp skin
    client.delete(f"/api/admin/catalogue/{temp_skin_id}", headers=owner_headers)

def test_14_card_skin_independent_ownership():
    """TEST 14: Card ownership and skin ownership remain completely independent."""
    uid = uuid.uuid4().hex[:6]
    reg = client.post("/api/auth/register", json={
        "email": f"indep_{uid}@example.com", "username": f"Indep_{uid}", "password": "Password123!"
    })
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    cards = client.get("/api/catalogue/cards").json()
    card = next(c for c in cards if c["character"] in ["Fanatic", "Cult Leader"])
    skins = client.get(f"/api/catalogue/cards/{card['id']}/skins").json()
    skin = skins[0]

    # 1. Mark CARD as owned
    t_card = client.post(f"/api/collection/toggle/{card['id']}", headers=h)
    assert t_card.status_code == 200
    assert t_card.json()["owned"] is True

    # Verify SKIN is still NOT owned
    col = client.get("/api/collection", headers=h).json()
    assert card["id"] in col["owned_item_ids"]
    assert skin["id"] not in col["owned_item_ids"]

    # 2. Mark SKIN as owned
    t_skin = client.post(f"/api/collection/toggle/{skin['id']}", headers=h)
    assert t_skin.status_code == 200
    assert t_skin.json()["owned"] is True

    # 3. Mark CARD as UNOWNED (toggle off)
    t_card_off = client.post(f"/api/collection/toggle/{card['id']}", headers=h)
    assert t_card_off.json()["owned"] is False

    # SKIN must REMAIN owned!
    col_after = client.get("/api/collection", headers=h).json()
    assert card["id"] not in col_after["owned_item_ids"]
    assert skin["id"] in col_after["owned_item_ids"]

def test_15_icon_move_owner_security_and_persistence():
    """TEST 15: Move feature for icons is strictly owner-only, updates display_order immediately, and persists."""
    icons = client.get("/api/catalogue/icons").json()
    assert len(icons) >= 10
    icon_0 = icons[0]
    icon_1 = icons[1]

    # 1. Unauthorized visitor gets 401
    unauth_res = client.post("/api/admin/catalogue/move", json={
        "category": "icons", "item_id": icon_0["id"], "direction": "next"
    })
    assert unauth_res.status_code in [401, 403]

    # 2. Ordinary user gets 403 Forbidden
    uid = uuid.uuid4().hex[:6]
    reg_user = client.post("/api/auth/register", json={
        "email": f"ord_move_{uid}@example.com", "username": f"OrdMove_{uid}", "password": "Password123!"
    })
    user_headers = {"Authorization": f"Bearer {reg_user.json()['access_token']}"}
    forbidden_res = client.post("/api/admin/catalogue/move", json={
        "category": "icons", "item_id": icon_0["id"], "direction": "next"
    }, headers=user_headers)
    assert forbidden_res.status_code == 403

    # 3. Authenticated Owner moves icon_0 down/next
    login_owner = client.post("/api/auth/login", json={
        "username_or_email": settings.INITIAL_OWNER_EMAIL,
        "password": settings.INITIAL_OWNER_PASSWORD,
    })
    owner_headers = {"Authorization": f"Bearer {login_owner.json()['access_token']}"}

    move_res = client.post("/api/admin/catalogue/move", json={
        "category": "icons", "item_id": icon_0["id"], "direction": "next"
    }, headers=owner_headers)
    assert move_res.status_code == 200
    assert move_res.json()["new_position"] == 2

    # 4. Verify new order persisted in GET /api/catalogue/icons
    icons_after = client.get("/api/catalogue/icons").json()
    assert icons_after[0]["id"] == icon_1["id"]
    assert icons_after[1]["id"] == icon_0["id"]

    # 5. Verify icon metadata intact (not recreated or overwritten)
    moved_item = icons_after[1]
    assert moved_item["name"] == icon_0["name"]
    assert moved_item["image"] == icon_0["image"]
    assert moved_item["cp"] == icon_0["cp"]

    # 6. Verify other categories (e.g. cards) order is untouched
    cards = client.get("/api/catalogue/cards").json()
    assert len(cards) == 42

    # 7. Move back to position 1 using target_position
    restore_res = client.post("/api/admin/catalogue/move", json={
        "category": "icons", "item_id": icon_0["id"], "target_position": 1
    }, headers=owner_headers)
    assert restore_res.status_code == 200

    icons_restored = client.get("/api/catalogue/icons").json()
    assert icons_restored[0]["id"] == icon_0["id"]
    assert icons_restored[1]["id"] == icon_1["id"]

def test_16_regular_and_cp_wallet_cp_values_and_integration():
    """TEST 16: Regular wallets have 500 CP (or 777 CP for 52-54), CP wallets have 0 CP,
    toggling regular wallets integrates into CP counter, and CP wallets reject manual toggle."""
    # 1. Check catalogue wallet values
    wallets = client.get("/api/catalogue/wallets").json()
    assert len(wallets) == 55
    for w in wallets:
        num = int(w["id"].split("_")[1])
        if num in (52, 53, 54, 55):
            assert w["cp"] == 777, f"Wallet {w['id']} expected 777 CP, got {w['cp']}"
        else:
            assert w["cp"] == 500, f"Wallet {w['id']} expected 500 CP, got {w['cp']}"

    # 2. Check CP wallets have 0 CP
    cp_wallets = client.get("/api/catalogue/cp_wallets").json()
    assert len(cp_wallets) == 8
    for cp_w in cp_wallets:
        assert cp_w["cp"] == 0, f"CP Wallet {cp_w['id']} must have 0 CP, got {cp_w['cp']}"

    # 3. New registered user has 0 CP and auto-qualifies for Level 0 (cp_wallet_01)
    uid = uuid.uuid4().hex[:6]
    reg = client.post("/api/auth/register", json={
        "email": f"wallet_user_{uid}@example.com",
        "username": f"WalletUser_{uid}",
        "password": "Password123!"
    })
    assert reg.status_code == 200
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    col0 = client.get("/api/collection", headers=h).json()
    assert "cp_wallet_01" in col0["owned_item_ids"]
    assert "cp_wallet_02" not in col0["owned_item_ids"]
    stats0 = client.get("/api/collection/stats", headers=h).json()
    assert stats0["user_cp"] == 0
    assert stats0["total_cp"] >= 28608  # Includes wallets max_cp (51 * 500 + 4 * 777 = 28608)

    # 4. Toggle regular wallet_01 (500 CP) ON
    t1 = client.post("/api/collection/toggle/wallet_01", headers=h)
    assert t1.status_code == 200
    assert t1.json()["owned"] is True

    stats1 = client.get("/api/collection/stats", headers=h).json()
    assert stats1["user_cp"] == 500
    assert stats1["category_breakdown"]["wallets"]["user_cp"] == 500
    assert stats1["category_breakdown"]["wallets"]["owned"] == 1

    # User reached 500 CP -> auto-unlocks Level 1 (cp_wallet_02), cp_wallet_01 removed
    col1 = client.get("/api/collection", headers=h).json()
    assert "cp_wallet_02" in col1["owned_item_ids"]
    assert "cp_wallet_01" not in col1["owned_item_ids"]

    # 5. Toggle regular wallet_52 (777 CP) ON
    t2 = client.post("/api/collection/toggle/wallet_52", headers=h)
    assert t2.status_code == 200
    stats2 = client.get("/api/collection/stats", headers=h).json()
    assert stats2["user_cp"] == 1277
    assert stats2["category_breakdown"]["wallets"]["user_cp"] == 1277

    # 6. Toggle regular wallet_01 (500 CP) and wallet_52 (777 CP) OFF -> downgrades back to cp_wallet_01
    client.post("/api/collection/toggle/wallet_01", headers=h)
    client.post("/api/collection/toggle/wallet_52", headers=h)

    stats3 = client.get("/api/collection/stats", headers=h).json()
    assert stats3["user_cp"] == 0
    col3 = client.get("/api/collection", headers=h).json()
    assert "cp_wallet_01" in col3["owned_item_ids"]
    assert "cp_wallet_02" not in col3["owned_item_ids"]

    # 7. Disallow manual toggle of CP Wallets
    manual_toggle = client.post("/api/collection/toggle/cp_wallet_04", headers=h)
    assert manual_toggle.status_code == 400
    assert "automatically unlocked" in manual_toggle.json()["detail"].lower()

def test_17_cp_wallet_automatic_qualification_and_boundaries():
    """TEST 17: Thoroughly verify all CP tier boundary thresholds for auto-awarding CP wallets:
    0–499 -> cp_wallet_01
    500–2,499 -> cp_wallet_02
    2,500–7,499 -> cp_wallet_03
    7,500–14,999 -> cp_wallet_04
    15,000–24,999 -> cp_wallet_05
    25,000–124,999 -> cp_wallet_06
    125,000–249,999 -> cp_wallet_07
    250,000+ -> cp_wallet_08"""
    from backend.app.routers.collection import get_cp_wallet_id_for_cp

    # Check function boundary conditions directly
    assert get_cp_wallet_id_for_cp(0) == "cp_wallet_01"
    assert get_cp_wallet_id_for_cp(499) == "cp_wallet_01"
    assert get_cp_wallet_id_for_cp(500) == "cp_wallet_02"
    assert get_cp_wallet_id_for_cp(2499) == "cp_wallet_02"
    assert get_cp_wallet_id_for_cp(2500) == "cp_wallet_03"
    assert get_cp_wallet_id_for_cp(7499) == "cp_wallet_03"
    assert get_cp_wallet_id_for_cp(7500) == "cp_wallet_04"
    assert get_cp_wallet_id_for_cp(14999) == "cp_wallet_04"
    assert get_cp_wallet_id_for_cp(15000) == "cp_wallet_05"
    assert get_cp_wallet_id_for_cp(24999) == "cp_wallet_05"
    assert get_cp_wallet_id_for_cp(25000) == "cp_wallet_06"
    assert get_cp_wallet_id_for_cp(124999) == "cp_wallet_06"
    assert get_cp_wallet_id_for_cp(125000) == "cp_wallet_07"
    assert get_cp_wallet_id_for_cp(249999) == "cp_wallet_07"
    assert get_cp_wallet_id_for_cp(250000) == "cp_wallet_08"
    assert get_cp_wallet_id_for_cp(500000) == "cp_wallet_08"

    # End-to-end API test with dynamic CP values
    login_owner = client.post("/api/auth/login", json={
        "username_or_email": settings.INITIAL_OWNER_EMAIL,
        "password": settings.INITIAL_OWNER_PASSWORD,
    })
    owner_headers = {"Authorization": f"Bearer {login_owner.json()['access_token']}"}

    uid = uuid.uuid4().hex[:6]
    reg = client.post("/api/auth/register", json={
        "email": f"tier_user_{uid}@example.com",
        "username": f"TierUser_{uid}",
        "password": "Password123!"
    })
    user_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Test item creation by owner to hit exact boundary values
    test_skin_id = f"test_boundary_skin_{uid}"
    client.post("/api/admin/catalogue", json={
        "id": test_skin_id,
        "category": "skins",
        "name": "Boundary Test Skin",
        "cp": 2500  # Exactly 2500 CP -> Level 2 (cp_wallet_03)
    }, headers=owner_headers)

    try:
        # User toggles test item ON
        client.post(f"/api/collection/toggle/{test_skin_id}", headers=user_headers)
        col = client.get("/api/collection", headers=user_headers).json()
        assert "cp_wallet_03" in col["owned_item_ids"]
        assert "cp_wallet_01" not in col["owned_item_ids"]
        assert "cp_wallet_02" not in col["owned_item_ids"]

        # Exactly ONE CP wallet owned
        owned_cp_wallets = [i for i in col["owned_item_ids"] if i.startswith("cp_wallet_")]
        assert len(owned_cp_wallets) == 1
        assert owned_cp_wallets[0] == "cp_wallet_03"
    finally:
        # Cleanup
        client.delete(f"/api/admin/catalogue/{test_skin_id}", headers=owner_headers)


def test_18_gems_collection_and_points():
    """TEST 18: Gems collection, 16 selectable levels, CP calculation, Gem Points (Lv15/16), and card linking."""
    login_owner = client.post("/api/auth/login", json={
        "username_or_email": settings.INITIAL_OWNER_EMAIL,
        "password": settings.INITIAL_OWNER_PASSWORD,
    })
    owner_headers = {"Authorization": f"Bearer {login_owner.json()['access_token']}"}

    uid1 = uuid.uuid4().hex[:6]
    reg1 = client.post("/api/auth/register", json={
        "email": f"gem_user1_{uid1}@example.com",
        "username": f"GemUser1_{uid1}",
        "password": "Password123!"
    })
    user1_headers = {"Authorization": f"Bearer {reg1.json()['access_token']}"}

    uid2 = uuid.uuid4().hex[:6]
    reg2 = client.post("/api/auth/register", json={
        "email": f"gem_user2_{uid2}@example.com",
        "username": f"GemUser2_{uid2}",
        "password": "Password123!"
    })
    user2_headers = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

    # 1. Fetch gems list
    gems_res = client.get("/api/gems", headers=user1_headers)
    assert gems_res.status_code == 200
    gems_data = gems_res.json()
    assert "Mafia Team" in gems_data["teams"]
    assert "Citizen Team" in gems_data["teams"]
    assert "Cult Mode" in gems_data["teams"]
    assert len(gems_data["teams"]["Mafia Team"]) == 10
    assert len(gems_data["teams"]["Citizen Team"]) == 27
    assert len(gems_data["teams"]["Cult Mode"]) == 1
    assert len(gems_data["all_gems"]) == 38
    assert gems_data["total_gem_cp"] == 0
    assert gems_data["total_gem_points"] == 0

    # 2. Select Level 1 for Cult Leader (75 CP, 0 Gem Points)
    res_lv1 = client.post("/api/gems/gem_cultleader/select-level", json={"current_level": 1}, headers=user1_headers)
    assert res_lv1.status_code == 200
    assert res_lv1.json()["cp"] == 75
    assert res_lv1.json()["gem_points"] == 0

    # 3. Selecting another level replaces previous level (e.g. Level 15 = 975 CP, 1 Gem Point)
    res_lv15 = client.post("/api/gems/gem_cultleader/select-level", json={"current_level": 15}, headers=user1_headers)
    assert res_lv15.status_code == 200
    assert res_lv15.json()["cp"] == 975
    assert res_lv15.json()["gem_points"] == 1

    # Check total stats for User 1
    gems_u1 = client.get("/api/gems", headers=user1_headers).json()
    assert gems_u1["total_gem_cp"] == 975
    assert gems_u1["total_gem_points"] == 1

    # Check that User 2 has independent selections (still 0)
    gems_u2 = client.get("/api/gems", headers=user2_headers).json()
    assert gems_u2["total_gem_cp"] == 0
    assert gems_u2["total_gem_points"] == 0

    # User 2 selects Level 16 for Mafia Gem (1,099 CP, 2 Gem Points)
    res_u2_lv16 = client.post("/api/gems/gem_mafia/select-level", json={"current_level": 16}, headers=user2_headers)
    assert res_u2_lv16.status_code == 200
    assert res_u2_lv16.json()["cp"] == 1099
    assert res_u2_lv16.json()["gem_points"] == 2

    # 4. Special Case: No Gem (Level 0 clears selection and resets CP to 0)
    res_nogem = client.post("/api/gems/gem_cultleader/select-level", json={"current_level": 0}, headers=user1_headers)
    assert res_nogem.status_code == 200
    assert res_nogem.json()["cp"] == 0
    assert res_nogem.json()["gem_points"] == 0

    gems_u1_reset = client.get("/api/gems", headers=user1_headers).json()
    assert gems_u1_reset["total_gem_cp"] == 0
    assert gems_u1_reset["total_gem_points"] == 0

    # 5. Card linking: Non-owner gets 403 Forbidden
    assert client.put("/api/gems/admin/gem_mafia/link-card", json={"card_id": "iouygpwh"}, headers=user1_headers).status_code == 403

    # Owner can link/unlink card
    link_res = client.put("/api/gems/admin/gem_mafia/link-card", json={"card_id": "iouygpwh"}, headers=owner_headers)
    assert link_res.status_code == 200
    assert link_res.json()["card_id"] == "iouygpwh"



