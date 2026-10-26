import os
import json
from sqlalchemy.orm import Session
from backend.app.models import User, UserProfile, CatalogueItem, AuditLog, UserCollectionItem
from backend.app.auth import get_password_hash
from backend.app.config import settings

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED_CATALOGUE_PATH = os.path.join(WORKSPACE_DIR, "database", "seed_catalogue.json")

def seed_database(db: Session):
    print("Checking database seed status...")
    
    # 1. Bootstrap Owner if not present
    existing_owner = db.query(User).filter(User.role == "owner").first()
    if not existing_owner:
        owner_user = User(
            email=settings.INITIAL_OWNER_EMAIL,
            username=settings.INITIAL_OWNER_USERNAME,
            hashed_password=get_password_hash(settings.INITIAL_OWNER_PASSWORD),
            role="owner",
            is_active=True,
        )
        db.add(owner_user)
        db.flush()
        
        owner_profile = UserProfile(
            user_id=owner_user.id,
            display_name=settings.INITIAL_OWNER_USERNAME,
            role_title="Game Master / Owner",
            joined_date="2026-10-11",
            bio="Administrator and catalogue curator for Mafia42 Collection Journal.",
        )
        db.add(owner_profile)
        
        audit = AuditLog(
            user_id=owner_user.id,
            action="BOOTSTRAP_OWNER_ACCOUNT",
            target_type="user",
            target_id=owner_user.id,
            details=f"Initial owner account bootstrapped for {owner_user.email}",
        )
        db.add(audit)
        db.commit()
        print(f"Created initial owner account: {settings.INITIAL_OWNER_EMAIL}")
    else:
        print(f"Owner account already exists: {existing_owner.username}")

    # 2. Reconcile and synchronize all Canonical Catalogue Items from seed_catalogue.json
    if os.path.exists(SEED_CATALOGUE_PATH):
        print(f"Synchronizing and reconciling catalogue items from {SEED_CATALOGUE_PATH}...")
        with open(SEED_CATALOGUE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        order_counter = 0
        categories_map = {
            "cards": "cards",
            "skins": "skins",
            "icons": "icons",
            "frames": "frames",
            "nameplates": "nameplates",
            "wallets": "wallets",
            "cp_wallets": "cp_wallets",
            "stickers": "stickers",
            "speech_bubbles": "speech_bubbles",
        }

        for cat_key, cat_name in categories_map.items():
            items_list = data.get(cat_key, [])
            for item in items_list:
                order_counter += 1
                item_id = item.get("id")
                c_item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
                if not c_item:
                    c_item = CatalogueItem(
                        id=item_id,
                        category=cat_name,
                        name=item.get("name", ""),
                        character=item.get("character", ""),
                        card_id=item.get("cardId") or item.get("card_id", ""),
                        rarity=item.get("rarity", ""),
                        level=item.get("level", 1),
                        cp=item.get("cp", 0),
                        description=item.get("description", ""),
                        condition=item.get("condition", ""),
                        how_to=item.get("howTo") or item.get("how_to", ""),
                        extra=item.get("extra", ""),
                        image=item.get("image", ""),
                        logo_image=item.get("logoImage") or item.get("logo_image", ""),
                        wallet_images=item.get("walletImages") or item.get("wallet_images", []),
                        display_order=item.get("display_order", order_counter),
                    )
                    db.add(c_item)
                else:
                    c_item.category = cat_name
                    c_item.name = item.get("name", c_item.name)
                    c_item.character = item.get("character", "")
                    c_item.card_id = item.get("cardId") or item.get("card_id", "")
                    c_item.rarity = item.get("rarity", "")
                    c_item.level = item.get("level", 1)
                    # Preserve existing database CP values for stickers and speech bubbles
                    if cat_name in ("stickers", "speech_bubbles") and c_item.cp is not None:
                        pass
                    else:
                        c_item.cp = item.get("cp", 0)
                    c_item.description = item.get("description", "")
                    c_item.condition = item.get("condition", "")
                    c_item.how_to = item.get("howTo") or item.get("how_to", "")
                    c_item.extra = item.get("extra", "")
                    c_item.image = item.get("image", "")
                    c_item.logo_image = item.get("logoImage") or item.get("logo_image", "")
                    c_item.wallet_images = item.get("walletImages") or item.get("wallet_images", [])
                    c_item.display_order = item.get("display_order", order_counter)

        # Safely purge extra non-canonical nameplates (e.g. 43 extra items in live database)
        canonical_np_ids = {item["id"] for item in data.get("nameplates", [])}
        extra_nps = db.query(CatalogueItem).filter(CatalogueItem.category == "nameplates", ~CatalogueItem.id.in_(canonical_np_ids)).all()
        if extra_nps:
            extra_np_ids = [np.id for np in extra_nps]
            print(f"Purging {len(extra_np_ids)} non-canonical nameplates from database: {extra_np_ids}")
            db.query(UserCollectionItem).filter(UserCollectionItem.item_id.in_(extra_np_ids)).delete(synchronize_session=False)
            db.query(CatalogueItem).filter(CatalogueItem.id.in_(extra_np_ids)).delete(synchronize_session=False)

        db.commit()
        total_synced = db.query(CatalogueItem).count()
        print(f"Catalogue items synchronized successfully ({total_synced} items present).")

    # 3. Ensure all 55 official regular wallets exist and are up to date
    REGULAR_WALLETS = [
        (1, "Yokai Wallet", "01-yokai-wallet"),
        (2, "Brilliance of the Zodiac", "02-brilliance-of-the-zodiac"),
        (3, "Mother-of-Pearl Jewelry Box", "03-mother-of-pearl-jewelry-box"),
        (4, "Blue Dragon Scepter", "04-blue-dragon-scepter"),
        (5, "Book of Dreams", "05-book-of-dreams"),
        (6, "Top Secret Frog Notebook", "06-top-secret-frog-notebook"),
        (7, "Checkered Pattern Wallet", "07-checkered-pattern-wallet"),
        (8, "Mansion Secret List", "08-mansion-secret-list"),
        (9, "Time Traveler's Wallet", "09-time-travelers-wallet"),
        (10, "Whipped Cream Ribbon Wallet", "10-whipped-cream-ribbon-wallet"),
        (11, "Old-Fashioned Killing Department", "11-old-fashioned-killing-department"),
        (12, "Genesis Side Story", "12-genesis-side-story"),
        (13, "Artist's Notebook", "13-artists-notebook"),
        (14, "Collector's Wallet", "14-collectors-wallet"),
        (15, "A Glorious Catalogue", "15-a-glorious-catalogue"),
        (16, "Spring Breeze Magazine", "16-spring-breeze-magazine"),
        (17, "Trump Wallet", "17-trump-wallet"),
        (18, "The Trump Wallet of the Underworld", "18-the-trump-wallet-of-the-underworld"),
        (19, "Welcome Trump Wallet", "19-welcome-trump-wallet"),
        (20, "Winner's Wallet", "20-winners-wallet"),
        (21, "Decree of the Black Kingdom", "21-decree-of-the-black-kingdom"),
        (22, "Frog Wallet", "22-frog-wallet"),
        (23, "Corgi Corgi Wallet", "23-corgi-corgi-wallet"),
        (24, "(Not Available)", "24-not-available"),
        (25, "Deep Sea Secret Wallet", "25-deep-sea-secret-wallet"),
        (26, "Star Sea Wallet", "26-star-sea-wallet"),
        (27, "Student Wallet", "27-student-wallet"),
        (28, "Honor Student ID Card", "28-honor-student-id-card"),
        (29, "Point Summary Note", "29-point-summary-note"),
        (30, "Pig Purse", "30-pig-purse"),
        (31, "Bunny Man Wallet", "31-bunny-man-wallet"),
        (32, "Purple Silk Purse", "32-purple-silk-purse"),
        (33, "Moon Rabbit's Space Wallet", "33-moon-rabbits-space-wallet"),
        (34, "First Aid Rabbit Bot Wallet", "34-first-aid-rabbit-bot-wallet"),
        (35, "Butterfly Group Corp. Employee ID Card", "35-butterfly-group-corp-employee-id-card"),
        (36, "Halloween Night Purse", "36-halloween-night-purse"),
        (37, "Invitee's Wallet", "37-invitees-wallet"),
        (38, "Discarded Shooting Records", "38-discarded-shooting-records"),
        (39, "Heir's Wallet", "39-heirs-wallet"),
        (40, "Classic Organizer", "40-classic-organizer"),
        (41, "Snowflake Wallet", "41-snowflake-wallet"),
        (42, "Winter Uniform Wallet", "42-winter-uniform-wallet"),
        (43, "Cozy Winter Wallet", "43-cozy-winter-wallet"),
        (44, "Mystic Winter Wallet", "44-mystic-winter-wallet"),
        (45, "Christmas Cat Wallet", "45-christmas-cat-wallet"),
        (46, "Fairy Photo Book", "46-fairy-photo-book"),
        (47, "Butterfly Group Corp. Executive Wallet", "47-butterfly-group-corp-executive-wallet"),
        (48, "Unidentified Battle Diary", "48-unidentified-battle-diary"),
        (49, "Guest List", "49-guest-list"),
        (50, "Pink Cat Pouch Wallet", "50-pink-cat-pouch-wallet"),
        (51, "Secret Prompt", "51-secret-prompt"),
        (52, "Winner's Wallet (Pickup period: ~ July 6, 2024)", "52-winners-wallet-pickup-period-july-6-2024"),
        (53, "Blue Clown's Wallet (Pickup period: July 7, 2024 ~ July 6, 2025)", "53-blue-clowns-wallet-pickup-period-july-7-2024-july-6-2025"),
        (54, "Winning Payment Book (Pickup period: July 7, 2025 ~ July 6, 2026)", "54-winning-payment-book-pickup-period-july-7-2025-july-6-2026"),
        (55, "Dice God Diary (Pickup period: July 7, 2026 ~ 2027)", "55-dice-god-diary-pickup-period-july-7-2026-2027"),
    ]
    for num, name, folder_name in REGULAR_WALLETS:
        has_asset = num != 24
        cp_val = 777 if num in (52, 53, 54, 55) else 500
        w_id = f"wallet_{num:02d}"
        existing_w = db.query(CatalogueItem).filter(CatalogueItem.id == w_id).first()
        if not existing_w:
            db.add(CatalogueItem(
                id=w_id,
                category="wallets",
                name=name,
                description="",
                cp=cp_val,
                image=f"/assets/wallets/{folder_name}/logo.png" if has_asset else "",
                logo_image=f"/assets/wallets/{folder_name}/logo.png" if has_asset else "",
                wallet_images=[
                    f"/assets/wallets/{folder_name}/1.png",
                    f"/assets/wallets/{folder_name}/2.png",
                    f"/assets/wallets/{folder_name}/3.png"
                ] if has_asset else [],
                display_order=num,
            ))
        else:
            existing_w.name = name
            existing_w.cp = cp_val
            existing_w.image = f"/assets/wallets/{folder_name}/logo.png" if has_asset else ""
            existing_w.logo_image = f"/assets/wallets/{folder_name}/logo.png" if has_asset else ""
            existing_w.wallet_images = [
                f"/assets/wallets/{folder_name}/1.png",
                f"/assets/wallets/{folder_name}/2.png",
                f"/assets/wallets/{folder_name}/3.png"
            ] if has_asset else []
            existing_w.display_order = num
    db.commit()

    # Safely purge obsolete sample wallets that were replaced by the 55 official regular wallets
    db.query(CatalogueItem).filter(CatalogueItem.id.in_(["m42_wallets_7b727ed7", "wallet_crimson_crest", "wallet_syndicate_black"])).delete(synchronize_session=False)
    db.commit()

    # 4. Ensure official CP wallets exist and are up to date
    CP_WALLETS = [
        (1, "Collection Point Level 0 Wallet", "01-collection-point-level-0-wallet", "0–499 CP"),
        (2, "Collection Point Level 1 Wallet", "02-collection-point-level-1-wallet", "500–2,499 CP"),
        (3, "Collection Point Level 2 Wallet", "03-collection-point-level-2-wallet", "2,500–7,499 CP"),
        (4, "Collection Point Level 3 Wallet", "04-collection-point-level-3-wallet", "7,500–14,999 CP"),
        (5, "Collection Point Level 4 Wallet", "05-collection-point-level-4-wallet", "15,000–24,999 CP"),
        (6, "Collection Point Level 5 Wallet", "06-collection-point-level-5-wallet", "25,000–124,999 CP"),
        (7, "Master Wallet", "07-master-wallet", "125,000–249,999 CP"),
        (8, "Grand Master Wallet", "08-grand-master-wallet", "250,000 CP or more"),
    ]
    for num, name, folder_name, cp_range in CP_WALLETS:
        cp_id = f"cp_wallet_{num:02d}"
        existing_cp = db.query(CatalogueItem).filter(CatalogueItem.id == cp_id).first()
        if not existing_cp:
            db.add(CatalogueItem(
                id=cp_id,
                category="cp_wallets",
                name=name,
                description="",
                condition=cp_range,
                cp=0,
                image=f"/assets/wallets/cp-wallets/{folder_name}/logo.png",
                logo_image=f"/assets/wallets/cp-wallets/{folder_name}/logo.png",
                wallet_images=[
                    f"/assets/wallets/cp-wallets/{folder_name}/1.png",
                    f"/assets/wallets/cp-wallets/{folder_name}/2.png",
                    f"/assets/wallets/cp-wallets/{folder_name}/3.png"
                ],
                display_order=num,
            ))
        else:
            existing_cp.name = name
            existing_cp.condition = cp_range
            existing_cp.cp = 0
            existing_cp.image = f"/assets/wallets/cp-wallets/{folder_name}/logo.png"
            existing_cp.logo_image = f"/assets/wallets/cp-wallets/{folder_name}/logo.png"
            existing_cp.wallet_images = [
                f"/assets/wallets/cp-wallets/{folder_name}/1.png",
                f"/assets/wallets/cp-wallets/{folder_name}/2.png",
                f"/assets/wallets/cp-wallets/{folder_name}/3.png"
            ]
            existing_cp.display_order = num
    db.commit()

    # 6. Ensure Gems exist and are up to date
    seed_gems_path = os.path.join(WORKSPACE_DIR, "database", "seed_gems.json")
    if os.path.exists(seed_gems_path):
        with open(seed_gems_path, "r", encoding="utf-8") as f:
            gems_data = json.load(f)
        for g in gems_data:
            g_team = "Cult Mode" if g.get("role_id") == "cultleader" or g.get("id") == "gem_cultleader" else g.get("team")
            extra_json = json.dumps({
                "team": g_team,
                "role_id": g.get("role_id"),
                "card_name": g.get("card_name"),
                "badge_image": g.get("badge_image"),
                "levels": g.get("levels", [])
            }, ensure_ascii=False)
            existing_gem = db.query(CatalogueItem).filter(CatalogueItem.id == g.get("id")).first()
            if not existing_gem:
                c_item = CatalogueItem(
                    id=g.get("id"),
                    category="gems",
                    name=g.get("name"),
                    character=g.get("character"),
                    card_id=g.get("card_id", ""),
                    level=16,
                    cp=1099,
                    description=f"{g_team} gem for {g.get('character')}",
                    extra=extra_json,
                    image=g.get("image", ""),
                    logo_image=g.get("badge_image", ""),
                    display_order=g.get("display_order", 0),
                )
                db.add(c_item)
            else:
                existing_gem.extra = extra_json
                existing_gem.name = g.get("name")
                existing_gem.character = g.get("character")
                existing_gem.image = g.get("image", "")
                existing_gem.logo_image = g.get("badge_image", "")
                existing_gem.description = f"{g_team} gem for {g.get('character')}"
        db.commit()

    # 7. Ensure Cult Leader is categorized under Cult Mode
    cult_gem = db.query(CatalogueItem).filter(CatalogueItem.id == "gem_cultleader").first()
    if cult_gem and cult_gem.extra:
        try:
            extra_data = json.loads(cult_gem.extra)
            if extra_data.get("team") != "Cult Mode":
                extra_data["team"] = "Cult Mode"
                cult_gem.extra = json.dumps(extra_data, ensure_ascii=False)
                cult_gem.description = "Cult Mode gem for Cult Leader"
                db.commit()
                print("Migrated Cult Leader to Cult Mode.")
        except Exception:
            pass

    # 8. Ensure existing wallet CP values match specification
    wallets = db.query(CatalogueItem).filter(CatalogueItem.category == "wallets").all()
    for w in wallets:
        try:
            num = int(w.id.split("_")[1])
            expected_cp = 777 if num in (52, 53, 54, 55) else 500
            if w.cp != expected_cp:
                w.cp = expected_cp
        except Exception:
            pass

    cp_wallets = db.query(CatalogueItem).filter(CatalogueItem.category == "cp_wallets").all()
    for cp_w in cp_wallets:
        if cp_w.cp != 0:
            cp_w.cp = 0
    db.commit()


