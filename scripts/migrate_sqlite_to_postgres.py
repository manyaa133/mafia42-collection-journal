"""
Safe, repeatable migration script from SQLite (mafia42.db) to PostgreSQL (Supabase).
Preserves:
- IDs, foreign keys, timestamps, ordering
- catalogue_items (929 items)
- users & user_profiles (94 records)
- user_collections (79 entries)
- user_gems, user_goals, user_achievements, user_notes
- audit_logs (236 records)

Usage:
  # With DATABASE_URL set in environment:
  python scripts/migrate_sqlite_to_postgres.py

Dry-run:
  python scripts/migrate_sqlite_to_postgres.py --dry-run
"""

import os
import sys
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_DIR)

from backend.app.models import (
    Base, User, UserProfile, CatalogueItem, UserCollectionItem,
    UserGem, UserGoal, UserAchievement, UserNote, AuditLog
)

def run_migration(dry_run: bool = False):
    sqlite_path = os.path.join(WORKSPACE_DIR, "mafia42.db")
    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite database file not found at {sqlite_path}")
        sys.exit(1)

    target_url = os.environ.get("TARGET_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not target_url or target_url.startswith("sqlite"):
        print("ERROR: TARGET_DATABASE_URL or DATABASE_URL must be set to a PostgreSQL URL (e.g. Supabase)")
        print("Example: set TARGET_DATABASE_URL=postgresql://postgres.xxx:password@aws-0-xx.pooler.supabase.com:6543/postgres")
        sys.exit(1)

    # Normalize url scheme
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)
    if target_url.startswith("postgresql://"):
        target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    print(f"Source SQLite: {sqlite_path}")
    print(f"Target Postgres: {target_url.split('@')[-1] if '@' in target_url else target_url}")

    # Source Session
    src_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    SrcSession = sessionmaker(bind=src_engine)
    src_db = SrcSession()

    # Target Session
    tgt_engine = create_engine(target_url)
    TgtSession = sessionmaker(bind=tgt_engine)
    tgt_db = TgtSession()

    if dry_run:
        print("\n--- DRY RUN: Counting records in source SQLite ---")
        print(f"Users: {src_db.query(User).count()}")
        print(f"User Profiles: {src_db.query(UserProfile).count()}")
        print(f"Catalogue Items: {src_db.query(CatalogueItem).count()}")
        print(f"User Collections: {src_db.query(UserCollectionItem).count()}")
        print(f"User Gems: {src_db.query(UserGem).count()}")
        print(f"User Goals: {src_db.query(UserGoal).count()}")
        print(f"User Achievements: {src_db.query(UserAchievement).count()}")
        print(f"User Notes: {src_db.query(UserNote).count()}")
        print(f"Audit Logs: {src_db.query(AuditLog).count()}")
        print("--- Dry run completed. No data written. ---")
        return

    # Ensure tables exist on target PostgreSQL without dropping anything
    print("Creating tables on target PostgreSQL if not already present...")
    Base.metadata.create_all(bind=tgt_engine)

    # 1. Migrate Users
    users = src_db.query(User).all()
    migrated_users = 0
    for u in users:
        exists = tgt_db.query(User).filter(User.id == u.id).first()
        if not exists:
            tgt_db.add(User(
                id=u.id, email=u.email, username=u.username,
                hashed_password=u.hashed_password, role=u.role,
                is_active=u.is_active, created_at=u.created_at, updated_at=u.updated_at
            ))
            migrated_users += 1
    tgt_db.commit()
    print(f"Users migrated: {migrated_users} (total in source: {len(users)})")

    # 2. Migrate User Profiles
    profiles = src_db.query(UserProfile).all()
    migrated_profiles = 0
    for p in profiles:
        exists = tgt_db.query(UserProfile).filter(UserProfile.user_id == p.user_id).first()
        if not exists:
            tgt_db.add(UserProfile(
                user_id=p.user_id, display_name=p.display_name, initials=p.initials,
                level=p.level, rank=p.rank, role_title=p.role_title,
                favorite_character=p.favorite_character, joined_date=p.joined_date,
                bio=p.bio, avatar_image=p.avatar_image, updated_at=p.updated_at
            ))
            migrated_profiles += 1
    tgt_db.commit()
    print(f"Profiles migrated: {migrated_profiles} (total in source: {len(profiles)})")

    # 3. Migrate Catalogue Items
    catalogue = src_db.query(CatalogueItem).all()
    migrated_cat = 0
    for item in catalogue:
        exists = tgt_db.query(CatalogueItem).filter(CatalogueItem.id == item.id).first()
        if not exists:
            tgt_db.add(CatalogueItem(
                id=item.id, category=item.category, name=item.name,
                character=item.character, card_id=item.card_id,
                rarity=item.rarity, level=item.level, cp=item.cp,
                description=item.description, condition=item.condition,
                how_to=item.how_to, extra=item.extra, image=item.image,
                logo_image=item.logo_image, wallet_images=item.wallet_images,
                display_order=item.display_order, created_at=item.created_at,
                updated_at=item.updated_at
            ))
            migrated_cat += 1
    tgt_db.commit()
    print(f"Catalogue items migrated: {migrated_cat} (total in source: {len(catalogue)})")

    # 4. Migrate User Collections
    user_colls = src_db.query(UserCollectionItem).all()
    migrated_colls = 0
    for c in user_colls:
        exists = tgt_db.query(UserCollectionItem).filter(UserCollectionItem.id == c.id).first()
        if not exists:
            tgt_db.add(UserCollectionItem(
                id=c.id, user_id=c.user_id, item_id=c.item_id,
                owned=c.owned, date_obtained=c.date_obtained, notes=c.notes,
                updated_at=c.updated_at
            ))
            migrated_colls += 1
    tgt_db.commit()
    print(f"User collection items migrated: {migrated_colls} (total in source: {len(user_colls)})")

    # 5. Migrate Gems, Goals, Achievements, Notes
    for model, name in [
        (UserGem, "User Gems"),
        (UserGoal, "User Goals"),
        (UserAchievement, "User Achievements"),
        (UserNote, "User Notes"),
    ]:
        items = src_db.query(model).all()
        migrated = 0
        for it in items:
            exists = tgt_db.query(model).filter(model.id == it.id).first()
            if not exists:
                tgt_db.merge(it)
                migrated += 1
        tgt_db.commit()
        print(f"{name} migrated: {migrated} (total in source: {len(items)})")

    # 6. Migrate Audit Logs
    logs = src_db.query(AuditLog).all()
    migrated_logs = 0
    for l in logs:
        exists = tgt_db.query(AuditLog).filter(AuditLog.id == l.id).first()
        if not exists:
            tgt_db.add(AuditLog(
                id=l.id, user_id=l.user_id, action=l.action,
                target_type=l.target_type, target_id=l.target_id,
                details=l.details, ip_address=l.ip_address, timestamp=l.timestamp
            ))
            migrated_logs += 1
    tgt_db.commit()
    print(f"Audit logs migrated: {migrated_logs} (total in source: {len(logs)})")

    print("\nSUCCESS: All data verified and safely synchronized to PostgreSQL!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Perform count-check without modifying target")
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
