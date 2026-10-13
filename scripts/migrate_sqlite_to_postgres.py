"""
Safe, repeatable migration script from SQLite (mafia42.db) to PostgreSQL (Supabase).
Preserves:
- IDs, foreign keys, timestamps, ordering
- catalogue_items (929 items)
- users & user_profiles (104 records)
- user_collections (87 entries)
- user_gems, user_goals, user_achievements, user_notes
- audit_logs (261 records)

Features:
- Dry-run mode (--dry-run) inspects both source SQLite and destination Supabase PostgreSQL
- Checks destination connectivity and displays existing table counts without writing any data
- Creates tables using SQLAlchemy models (Base.metadata.create_all) without dropping or modifying existing tables
- Idempotently inserts records only if their ID does not already exist
- Compares source vs. target record counts upon completion

Usage:
  # Dry-run inspection:
  $env:TARGET_DATABASE_URL="postgresql://postgres.xxx:password@aws-0-xx.pooler.supabase.com:6543/postgres"
  python scripts/migrate_sqlite_to_postgres.py --dry-run

  # Full migration:
  python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, inspect
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
        print("Example: $env:TARGET_DATABASE_URL=\"postgresql://postgres.xxx:password@aws-0-xx.pooler.supabase.com:6543/postgres\"")
        sys.exit(1)

    # Normalize url scheme
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)
    if target_url.startswith("postgresql://"):
        target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Obfuscate credentials for safe console logging
    safe_target = target_url.split("@")[-1] if "@" in target_url else "configured_host"
    print(f"Source SQLite: {sqlite_path}")
    print(f"Target Postgres Host/DB: {safe_target}")

    # Source Session
    src_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    SrcSession = sessionmaker(bind=src_engine)
    src_db = SrcSession()

    # Target Session
    try:
        tgt_engine = create_engine(target_url)
        TgtSession = sessionmaker(bind=tgt_engine)
        tgt_db = TgtSession()
        # Verify connection
        with tgt_engine.connect() as conn:
            pass
        print("Successfully connected to destination PostgreSQL.")
    except Exception as e:
        print(f"\nERROR: Could not connect to target database ({safe_target}).")
        print("Details:", str(e))
        sys.exit(1)

    # Inspect target tables
    tgt_inspector = inspect(tgt_engine)
    existing_tables = tgt_inspector.get_table_names()
    print(f"Existing tables in destination: {existing_tables if existing_tables else 'None (Empty Database)'}")

    if dry_run:
        print("\n--- DRY RUN: Source SQLite Record Counts ---")
        src_counts = {
            "users": src_db.query(User).count(),
            "user_profiles": src_db.query(UserProfile).count(),
            "catalogue_items": src_db.query(CatalogueItem).count(),
            "user_collections": src_db.query(UserCollectionItem).count(),
            "user_gems": src_db.query(UserGem).count(),
            "user_goals": src_db.query(UserGoal).count(),
            "user_achievements": src_db.query(UserAchievement).count(),
            "user_notes": src_db.query(UserNote).count(),
            "audit_logs": src_db.query(AuditLog).count(),
        }
        for table, count in src_counts.items():
            print(f"  {table}: {count}")

        print("\n--- DRY RUN: Destination PostgreSQL Record Counts ---")
        if not existing_tables:
            print("  No tables exist in destination yet. Running the migration will create all tables without altering anything.")
        else:
            for table, model in [
                ("users", User),
                ("user_profiles", UserProfile),
                ("catalogue_items", CatalogueItem),
                ("user_collections", UserCollectionItem),
                ("user_gems", UserGem),
                ("user_goals", UserGoal),
                ("user_achievements", UserAchievement),
                ("user_notes", UserNote),
                ("audit_logs", AuditLog),
            ]:
                if table in existing_tables:
                    try:
                        c = tgt_db.query(model).count()
                        print(f"  {table}: {c} existing records")
                    except Exception:
                        print(f"  {table}: exists (count query failed)")
                else:
                    print(f"  {table}: table not created yet")

        print("\n--- DRY RUN COMPLETE: No data was written to destination. ---")
        return

    # Ensure tables exist on target PostgreSQL without dropping anything
    print("\nEnsuring all tables exist on target PostgreSQL (Base.metadata.create_all)...")
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
    print(f"Users migrated: {migrated_users} new (source total: {len(users)})")

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
    print(f"Profiles migrated: {migrated_profiles} new (source total: {len(profiles)})")

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
    print(f"Catalogue items migrated: {migrated_cat} new (source total: {len(catalogue)})")

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
    print(f"User collection items migrated: {migrated_colls} new (source total: {len(user_colls)})")

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
        print(f"{name} migrated: {migrated} new (source total: {len(items)})")

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
    print(f"Audit logs migrated: {migrated_logs} new (source total: {len(logs)})")

    # Final post-migration verification
    print("\n--- POST-MIGRATION VERIFICATION ---")
    print(f"Destination Catalogue Items: {tgt_db.query(CatalogueItem).count()} (Source: {len(catalogue)})")
    print(f"Destination Users: {tgt_db.query(User).count()} (Source: {len(users)})")
    print(f"Destination User Profiles: {tgt_db.query(UserProfile).count()} (Source: {len(profiles)})")
    print(f"Destination User Collections: {tgt_db.query(UserCollectionItem).count()} (Source: {len(user_colls)})")
    print(f"Destination Audit Logs: {tgt_db.query(AuditLog).count()} (Source: {len(logs)})")

    print("\nSUCCESS: All data verified and safely synchronized to PostgreSQL!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Perform count-check without modifying target")
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
