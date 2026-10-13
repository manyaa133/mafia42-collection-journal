import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "owner" | "user"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    collection_items = relationship("UserCollectionItem", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("UserNote", back_populates="user", cascade="all, delete-orphan")
    gems = relationship("UserGem", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name = Column(String(100), default="")
    initials = Column(String(10), default="")
    level = Column(String(50), default="")
    rank = Column(String(50), default="")
    role_title = Column(String(100), default="")
    favorite_character = Column(String(100), default="")
    joined_date = Column(String(50), default="")
    bio = Column(Text, default="")
    avatar_image = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

class CatalogueItem(Base):
    __tablename__ = "catalogue_items"

    id = Column(String(100), primary_key=True)
    category = Column(String(50), index=True, nullable=False)  # skins, icons, cards, wallets, nameplates, frames, gems, postcards, refinements
    name = Column(String(255), nullable=False, default="")
    character = Column(String(100), default="")
    card_id = Column(String(100), default="")
    rarity = Column(String(50), default="")
    level = Column(Integer, default=1)
    cp = Column(Integer, default=0)
    description = Column(Text, default="")
    condition = Column(Text, default="")
    how_to = Column(Text, default="")
    extra = Column(Text, default="")
    image = Column(Text, default="")
    logo_image = Column(Text, default="")
    wallet_images = Column(JSON, default=list)  # list of 3 image URLs for wallets
    display_order = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_collections = relationship("UserCollectionItem", back_populates="catalogue_item", cascade="all, delete-orphan")

class UserCollectionItem(Base):
    __tablename__ = "user_collections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(100), ForeignKey("catalogue_items.id", ondelete="CASCADE"), nullable=False, index=True)
    owned = Column(Boolean, default=True, nullable=False)
    date_obtained = Column(String(50), default="")
    notes = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_collection_item"),
    )

    user = relationship("User", back_populates="collection_items")
    catalogue_item = relationship("CatalogueItem", back_populates="user_collections")

class UserGem(Base):
    __tablename__ = "user_gems"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(100), ForeignKey("catalogue_items.id", ondelete="CASCADE"), nullable=False, index=True)
    current_level = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_gem"),
    )

    user = relationship("User", back_populates="gems")

class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    current_val = Column(Integer, default=0)
    target_val = Column(Integer, default=1)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="goals")

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    date_obtained = Column(String(50), default="")
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")

class UserNote(Base):
    __tablename__ = "user_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="")
    content = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), default="")
    target_id = Column(String(100), default="")
    details = Column(Text, default="")
    ip_address = Column(String(50), default="")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

