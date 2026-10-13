from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Auth Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Profile Schemas
class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    initials: Optional[str] = None
    level: Optional[str] = None
    rank: Optional[str] = None
    role_title: Optional[str] = None
    favorite_character: Optional[str] = None
    joined_date: Optional[str] = None
    bio: Optional[str] = None
    avatar_image: Optional[str] = None

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str = ""
    initials: str = ""
    level: str = ""
    rank: str = ""
    role_title: str = ""
    favorite_character: str = ""
    joined_date: str = ""
    bio: str = ""
    avatar_image: str = ""

# Catalogue Schemas
class CatalogueItemBase(BaseModel):
    id: Optional[str] = None
    category: str
    name: str
    character: Optional[str] = ""
    card_id: Optional[str] = ""
    rarity: Optional[str] = ""
    level: Optional[int] = 1
    cp: Optional[int] = 0
    description: Optional[str] = ""
    condition: Optional[str] = ""
    how_to: Optional[str] = ""
    extra: Optional[str] = ""
    image: Optional[str] = ""
    logo_image: Optional[str] = ""
    wallet_images: Optional[List[str]] = Field(default_factory=list)
    display_order: Optional[int] = 0

class CatalogueItemCreate(CatalogueItemBase):
    pass

class CatalogueItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    character: Optional[str] = None
    card_id: Optional[str] = None
    rarity: Optional[str] = None
    level: Optional[int] = None
    cp: Optional[int] = None
    description: Optional[str] = None
    condition: Optional[str] = None
    how_to: Optional[str] = None
    extra: Optional[str] = None
    image: Optional[str] = None
    logo_image: Optional[str] = None
    wallet_images: Optional[List[str]] = None
    display_order: Optional[int] = None

class CatalogueItemResponse(CatalogueItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CatalogueReorderRequest(BaseModel):
    category: str
    item_ids: List[str]

class CatalogueItemMoveRequest(BaseModel):
    category: str = "icons"
    item_id: str
    direction: Optional[str] = None  # "up", "down", "prev", "next"
    target_position: Optional[int] = None  # 1-indexed target position

class CatalogueImportRequest(BaseModel):
    data: Dict[str, List[Dict[str, Any]]]

# Collection Schemas
class CollectionToggleRequest(BaseModel):
    item_id: str
    owned: Optional[bool] = None  # If None, will toggle

class CollectionItemUpdate(BaseModel):
    owned: bool
    date_obtained: Optional[str] = ""
    notes: Optional[str] = ""

class CollectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    owned: bool
    date_obtained: str = ""
    notes: str = ""

class CPStatsResponse(BaseModel):
    total_cp: int
    user_cp: int
    completion_percentage: float
    category_breakdown: Dict[str, Dict[str, Any]]
    total_items: int
    owned_items: int

# Gem Schemas
class GemLevelUpdate(BaseModel):
    current_level: int = Field(..., ge=0, le=16)

# Goal Schemas
class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    current_val: Optional[int] = 0
    target_val: Optional[int] = 1

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    current_val: Optional[int] = None
    target_val: Optional[int] = None
    completed: Optional[bool] = None

class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    current_val: int
    target_val: int
    completed: bool

# Note Schemas
class NoteCreate(BaseModel):
    title: Optional[str] = ""
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

# Admin Schemas
class UserAdminView(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    owned_items_count: int

class UserStatusUpdate(BaseModel):
    is_active: bool

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str]
    action: str
    target_type: str
    target_id: str
    details: str
    ip_address: str
    timestamp: datetime
