import sys
import os

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_DIR)

from backend.app.database import SessionLocal
from backend.app.models import User, UserProfile, AuditLog
from backend.app.auth import get_password_hash
from backend.app.config import settings

def bootstrap_owner(email=None, username=None, password=None):
    email = email or settings.INITIAL_OWNER_EMAIL
    username = username or settings.INITIAL_OWNER_USERNAME
    password = password or settings.INITIAL_OWNER_PASSWORD

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == "owner").first()
        if user:
            print(f"Owner account exists: {user.username} ({user.email}). Updating credentials...")
            user.email = email
            user.username = username
            user.hashed_password = get_password_hash(password)
            user.is_active = True
        else:
            print(f"Creating new owner account: {username} ({email})...")
            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                role="owner",
                is_active=True,
            )
            db.add(user)
            db.flush()

            profile = UserProfile(
                user_id=user.id,
                display_name=username,
                role_title="Game Master / Owner",
                joined_date="2026-10-11",
                bio="Administrator and catalogue curator for Mafia42 Collection Journal."
            )
            db.add(profile)

        audit = AuditLog(
            user_id=user.id,
            action="BOOTSTRAP_OWNER_CLI",
            target_type="user",
            target_id=user.id,
            details=f"Owner account provisioned via CLI: {username} ({email})",
        )
        db.add(audit)
        db.commit()
        print("Owner account successfully configured.")
    finally:
        db.close()

if __name__ == "__main__":
    e = sys.argv[1] if len(sys.argv) > 1 else None
    u = sys.argv[2] if len(sys.argv) > 2 else None
    p = sys.argv[3] if len(sys.argv) > 3 else None
    bootstrap_owner(e, u, p)

