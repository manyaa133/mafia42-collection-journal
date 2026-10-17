from typing import Dict, Any, List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, CatalogueItem, UserGem, AuditLog
from backend.app.auth import get_current_user, get_current_owner, get_optional_user
from backend.app.schemas import GemLevelUpdate, CatalogueItemResponse
from backend.app.routers.collection import sync_user_cp_wallet

router = APIRouter(prefix="/gems", tags=["Gems Collection"])

# Standard CP and Gem Points by Level
LEVEL_CP_MAP = {
    0: (0, 0),
    1: (75, 0),
    2: (91, 0),
    3: (111, 0),
    4: (139, 0),
    5: (175, 0),
    6: (219, 0),
    7: (271, 0),
    8: (331, 0),
    9: (399, 0),
    10: (475, 0),
    11: (559, 0),
    12: (651, 0),
    13: (751, 0),
    14: (859, 0),
    15: (975, 1),
    16: (1099, 2),
}

@router.get("", response_model=Dict[str, Any])
def get_user_gems_and_catalogue(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Fetch all gems organized by team and role, with the user's currently selected level,
    total gem CP contribution, and total Gem Points. Works for both authenticated users
    and guest visitors.
    """
    gem_items = db.query(CatalogueItem).filter(
        CatalogueItem.category == "gems"
    ).order_by(CatalogueItem.display_order.asc()).all()

    user_levels_map = {}
    user_id_val = ""
    if current_user:
        user_id_val = current_user.id
        user_gems = db.query(UserGem).filter(UserGem.user_id == current_user.id).all()
        user_levels_map = {ug.item_id: ug.current_level for ug in user_gems}

    mafia_gems = []
    citizen_gems = []
    cult_gems = []
    total_gem_cp = 0
    total_gem_points = 0

    for item in gem_items:
        current_lvl = user_levels_map.get(item.id, 0)
        cp_val, gp_val = LEVEL_CP_MAP.get(current_lvl, (0, 0))
        total_gem_cp += cp_val
        total_gem_points += gp_val

        # Parse extra info (team, levels array, badge_image, etc.)
        extra_data = {}
        if item.extra:
            try:
                extra_data = json.loads(item.extra)
            except Exception:
                pass

        levels = extra_data.get("levels", [])
        team = extra_data.get("team", "Citizen Team")
        role_id = extra_data.get("role_id", item.character.lower().replace(" ", ""))
        card_name = extra_data.get("card_name", item.character)
        badge_image = extra_data.get("badge_image", item.logo_image or "")

        # Find linked card details if card_id exists
        linked_card = None
        if item.card_id:
            card_obj = db.query(CatalogueItem).filter(
                CatalogueItem.category == "cards",
                CatalogueItem.id == item.card_id
            ).first()
            if card_obj:
                linked_card = {
                    "id": card_obj.id,
                    "name": card_obj.name,
                    "character": card_obj.character,
                    "image": card_obj.image,
                }

        # Current level item details
        current_level_data = None
        if current_lvl > 0 and current_lvl <= len(levels):
            current_level_data = levels[current_lvl - 1]

        gem_data = {
            "id": item.id,
            "category": "gems",
            "team": team,
            "role_id": role_id,
            "name": item.name,
            "character": item.character,
            "card_id": item.card_id,
            "card_name": card_name,
            "linked_card": linked_card,
            "image": item.image,
            "badge_image": badge_image,
            "display_order": item.display_order,
            "current_level": current_lvl,
            "current_cp": cp_val,
            "current_gem_points": gp_val,
            "current_level_data": current_level_data,
            "levels": levels,
        }

        if team == "Mafia Team":
            mafia_gems.append(gem_data)
        elif team == "Cult Mode":
            cult_gems.append(gem_data)
        else:
            citizen_gems.append(gem_data)

    return {
        "user_id": user_id_val,
        "total_gem_cp": total_gem_cp,
        "total_gem_points": total_gem_points,
        "teams": {
            "Mafia Team": mafia_gems,
            "Citizen Team": citizen_gems,
            "Cult Mode": cult_gems,
        },
        "all_gems": mafia_gems + citizen_gems + cult_gems,
    }

@router.post("/{gem_id}/select-level")
def select_gem_level(
    gem_id: str,
    req: GemLevelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Select or change the user's level for a gem (1–16).
    Setting level to 0 acts as 'No Gem' (clears selection, 0 CP).
    Only one level can be active at a time for any given gem.
    """
    gem_item = db.query(CatalogueItem).filter(
        CatalogueItem.category == "gems",
        CatalogueItem.id == gem_id
    ).first()
    if not gem_item:
        raise HTTPException(status_code=404, detail="Gem not found")

    if req.current_level < 0 or req.current_level > 16:
        raise HTTPException(status_code=400, detail="Level must be between 0 (No Gem) and 16")

    record = db.query(UserGem).filter(
        UserGem.user_id == current_user.id,
        UserGem.item_id == gem_id
    ).first()

    if record:
        record.current_level = req.current_level
    else:
        record = UserGem(
            user_id=current_user.id,
            item_id=gem_id,
            current_level=req.current_level
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    # Immediately recalculate and sync CP wallet ownership tier
    sync_user_cp_wallet(current_user.id, db)

    cp_val, gp_val = LEVEL_CP_MAP.get(record.current_level, (0, 0))

    return {
        "message": "Gem level updated successfully",
        "gem_id": gem_id,
        "current_level": record.current_level,
        "cp": cp_val,
        "gem_points": gp_val,
    }

@router.put("/admin/{gem_id}/link-card")
def link_gem_card(
    gem_id: str,
    payload: Dict[str, Optional[str]],
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Owner-only endpoint to link, change, or unlink a card for a gem.
    Payload: {"card_id": "..."} or {"card_id": ""}
    """
    gem_item = db.query(CatalogueItem).filter(
        CatalogueItem.category == "gems",
        CatalogueItem.id == gem_id
    ).first()
    if not gem_item:
        raise HTTPException(status_code=404, detail="Gem not found")

    new_card_id = payload.get("card_id", "").strip() if payload.get("card_id") else ""
    card_name = ""

    if new_card_id:
        card = db.query(CatalogueItem).filter(
            CatalogueItem.category == "cards",
            CatalogueItem.id == new_card_id
        ).first()
        if not card:
            raise HTTPException(status_code=404, detail="Target card not found in catalogue")
        card_name = card.name

    gem_item.card_id = new_card_id

    # Also update card_id and card_name in extra json if present
    if gem_item.extra:
        try:
            extra_data = json.loads(gem_item.extra)
            extra_data["card_name"] = card_name
            gem_item.extra = json.dumps(extra_data, ensure_ascii=False)
        except Exception:
            pass

    audit = AuditLog(
        user_id=owner.id,
        action="GEM_CARD_LINK",
        target_type="gem",
        target_id=gem_id,
        details=f"Linked gem {gem_id} to card '{card_name}' ({new_card_id})" if new_card_id else f"Unlinked card from gem {gem_id}",
    )
    db.add(audit)
    db.commit()
    db.refresh(gem_item)

    return {
        "message": "Gem card link updated successfully",
        "gem_id": gem_id,
        "card_id": new_card_id,
        "card_name": card_name
    }

