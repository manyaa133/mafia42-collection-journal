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

    # 3. Ensure sample wallets exist if category is empty
    wallet_count = db.query(CatalogueItem).filter(CatalogueItem.category == "wallets").count()
    if wallet_count == 0:
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
                "display_order": 9991
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
                "display_order": 9992
            }
        ]
        for sw in sample_wallets:
            db.add(CatalogueItem(**sw))
        db.commit()
        print("Sample wallets seeded.")

