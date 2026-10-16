import os
import json
from sqlalchemy.orm import Session
from backend.app.models import User, UserProfile, CatalogueItem, AuditLog
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

    # 2. Seed Catalogue Items if table is empty
    item_count = db.query(CatalogueItem).count()
    if item_count == 0 and os.path.exists(SEED_CATALOGUE_PATH):
        print(f"Seeding catalogue items from {SEED_CATALOGUE_PATH}...")
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
        }

        for cat_key, cat_name in categories_map.items():
            items_list = data.get(cat_key, [])
            for item in items_list:
                order_counter += 1
                c_item = CatalogueItem(
                    id=item.get("id"),
                    category=cat_name,
                    name=item.get("name", ""),
                    character=item.get("character", ""),
                    card_id=item.get("cardId") or item.get("card_id", ""),
                    rarity=item.get("rarity", ""),
                    level=item.get("level", 1),
                    cp=item.get("cp", 0),
                    description=item.get("description", ""),
                    condition=item.get("condition", ""),
                    how_to=item.get("howTo", ""),
                    extra=item.get("extra", ""),
                    image=item.get("image", ""),
                    logo_image=item.get("logoImage", ""),
                    wallet_images=item.get("walletImages", []),
                    display_order=order_counter,
                )
                db.add(c_item)

        # Ensure sample wallets exist if catalogue has 0 wallets
        wallet_items = data.get("wallets", [])
        if len(wallet_items) == 0:
            sample_wallets = [
                {
                    "id": "wallet_syndicate_black",
                    "category": "wallets",
                    "name": "Syndicate Black Leather Wallet",
                    "description": "An exclusive black leather wallet stamped with the Mafia gold seal.",
                    "cp": 500,
                    "image": "/assets/cards/card_logo_m42-card-cop.jpg",
                    "logo_image": "/assets/cards/card_logo_m42-card-cop.jpg",
                    "wallet_images": [
                        "/assets/cards/card_m42-card-cop.jpg",
                        "/assets/skins/skin_logo_2ydoa5w8.jpg",
                        "/assets/frames/frame_8bn335dz.jpg"
                    ],
                    "display_order": order_counter + 1
                },
                {
                    "id": "wallet_crimson_crest",
                    "category": "wallets",
                    "name": "Crimson Crest Velvet Wallet",
                    "description": "Crafted from crimson velvet with embroidered silver accents.",
                    "cp": 750,
                    "image": "/assets/cards/card_logo_m42-card-mafia.jpg",
                    "logo_image": "/assets/cards/card_logo_m42-card-mafia.jpg",
                    "wallet_images": [
                        "/assets/cards/card_m42-card-mafia.jpg",
                        "/assets/skins/skin_logo_j5mk8zxe.jpg",
                        "/assets/frames/frame_m42-frame-001.jpg"
                    ],
                    "display_order": order_counter + 2
                }
            ]
            for sw in sample_wallets:
                # Only use valid assets if exist, else fallback gracefully
                db.add(CatalogueItem(**sw))

        db.commit()
        total_seeded = db.query(CatalogueItem).count()
        print(f"Successfully seeded {total_seeded} catalogue items into database.")
    else:
        print(f"Catalogue items already seeded ({item_count} items present).")

    # 3. Ensure official wallets exist if category is empty
    wallet_count = db.query(CatalogueItem).filter(CatalogueItem.category == "wallets").count()
    if wallet_count == 0:
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
            (24, "Deep Sea Secret Wallet", "24-deep-sea-secret-wallet"),
            (25, "Star Sea Wallet", "25-star-sea-wallet"),
            (26, "Student Wallet", "26-student-wallet"),
            (27, "Honor Student ID Card", "27-honor-student-id-card"),
            (28, "Point Summary Note", "28-point-summary-note"),
            (29, "Pig Purse", "29-pig-purse"),
            (30, "Bunny Man Wallet", "30-bunny-man-wallet"),
            (31, "Purple Silk Purse", "31-purple-silk-purse"),
            (32, "Moon Rabbit's Space Wallet", "32-moon-rabbits-space-wallet"),
            (33, "First Aid Rabbit Bot Wallet", "33-first-aid-rabbit-bot-wallet"),
            (34, "Butterfly Group Corp. Employee ID Card", "34-butterfly-group-corp-employee-id-card"),
            (35, "Halloween Night Purse", "35-halloween-night-purse"),
            (36, "Invitee's Wallet", "36-invitees-wallet"),
            (37, "Discarded Shooting Records", "37-discarded-shooting-records"),
            (38, "Heir's Wallet", "38-heirs-wallet"),
            (39, "Classic Organizer", "39-classic-organizer"),
            (40, "Luxury Card Case", "40-luxury-card-case"),
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
            cp_val = 777 if num in (52, 53, 54) else 500
            db.add(CatalogueItem(
                id=f"wallet_{num:02d}",
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
        db.commit()
        print("Official wallets seeded.")

    # 4. Ensure official CP wallets exist if category is empty
    cp_wallet_count = db.query(CatalogueItem).filter(CatalogueItem.category == "cp_wallets").count()
    if cp_wallet_count == 0:
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
            db.add(CatalogueItem(
                id=f"cp_wallet_{num:02d}",
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
        db.commit()
        print("Official CP wallets seeded.")

    # 5. Ensure existing wallet CP values match specification
    wallets = db.query(CatalogueItem).filter(CatalogueItem.category == "wallets").all()
    for w in wallets:
        try:
            num = int(w.id.split("_")[1])
            expected_cp = 777 if num in (52, 53, 54) else 500
            if w.cp != expected_cp:
                w.cp = expected_cp
        except Exception:
            pass

    cp_wallets = db.query(CatalogueItem).filter(CatalogueItem.category == "cp_wallets").all()
    for cp_w in cp_wallets:
        if cp_w.cp != 0:
            cp_w.cp = 0
    db.commit()

