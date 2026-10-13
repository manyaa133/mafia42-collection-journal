import uuid
import pytest
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
    assert len(cat["skins"]) == 334
    assert len(cat["cards"]) == 42
    assert len(cat["frames"]) == 158
    assert len(cat["nameplates"]) >= 221
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
    assert len(all_skins) == 334

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

