from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, CatalogueItem, UserCollectionItem, UserGem
from backend.app.schemas import CollectionItemResponse, CollectionItemUpdate, CPStatsResponse
from backend.app.auth import get_current_user

router = APIRouter(prefix="/collection", tags=["Personal Collection"])

CP_CATEGORIES = {"skins", "gems", "frames", "nameplates", "wallets", "stickers", "speech_bubbles"}

def get_cp_wallet_id_for_cp(user_cp: int) -> str:
    """Determine the eligible CP Wallet ID based on total collection points."""
    if user_cp >= 250000:
        return "cp_wallet_08"
    elif user_cp >= 125000:
        return "cp_wallet_07"
    elif user_cp >= 25000:
        return "cp_wallet_06"
    elif user_cp >= 15000:
        return "cp_wallet_05"
    elif user_cp >= 7500:
        return "cp_wallet_04"
    elif user_cp >= 2500:
        return "cp_wallet_03"
    elif user_cp >= 500:
        return "cp_wallet_02"
    else:
        return "cp_wallet_01"

GEM_LEVEL_CP_MAP = {
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

def calculate_user_cp(user_id: int, db: Session) -> int:
    """Calculate the total CP earned by the user across all eligible categories."""
    # Standard owned items (skins, frames, nameplates, wallets, stickers, speech_bubbles)
    standard_categories = {"skins", "frames", "nameplates", "wallets", "stickers", "speech_bubbles"}
    owned_items = (
        db.query(CatalogueItem.cp)
        .join(UserCollectionItem, UserCollectionItem.item_id == CatalogueItem.id)
        .filter(
            UserCollectionItem.user_id == user_id,
            UserCollectionItem.owned == True,
            CatalogueItem.category.in_(standard_categories)
        )
        .all()
    )
    standard_cp = sum(int(item[0] or 0) for item in owned_items)

    # Gems CP: calculated from user's selected level in user_gems
    user_gems = db.query(UserGem).filter(UserGem.user_id == user_id).all()
    gem_cp = sum(GEM_LEVEL_CP_MAP.get(ug.current_level, (0, 0))[0] for ug in user_gems)

    return standard_cp + gem_cp

def sync_user_cp_wallet(user_id: int, db: Session) -> str:
    """Ensure exactly one CP wallet matching the user's active CP bracket is owned."""
    user_cp = calculate_user_cp(user_id, db)
    eligible_wallet_id = get_cp_wallet_id_for_cp(user_cp)

    cp_wallets = (
        db.query(CatalogueItem.id)
        .filter(CatalogueItem.category == "cp_wallets")
        .all()
    )
    cp_wallet_ids = [w[0] for w in cp_wallets]
    if not cp_wallet_ids:
        cp_wallet_ids = [f"cp_wallet_{i:02d}" for i in range(1, 9)]

    existing_cp_records = (
        db.query(UserCollectionItem)
        .filter(
            UserCollectionItem.user_id == user_id,
            UserCollectionItem.item_id.in_(cp_wallet_ids)
        )
        .all()
    )
    record_map = {r.item_id: r for r in existing_cp_records}

    # Ensure the single eligible CP wallet is marked owned
    target_record = record_map.get(eligible_wallet_id)
    if target_record:
        if not target_record.owned:
            target_record.owned = True
    else:
        new_record = UserCollectionItem(
            user_id=user_id,
            item_id=eligible_wallet_id,
            owned=True,
        )
        db.add(new_record)

    # Ensure all other CP wallets are marked unowned
    for cp_id in cp_wallet_ids:
        if cp_id != eligible_wallet_id and cp_id in record_map:
            if record_map[cp_id].owned:
                record_map[cp_id].owned = False

    db.commit()
    return eligible_wallet_id

@router.get("", response_model=Dict[str, Any])
def get_user_collection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sync_user_cp_wallet(current_user.id, db)

    items = db.query(UserCollectionItem).filter(
        UserCollectionItem.user_id == current_user.id,
        UserCollectionItem.owned == True
    ).all()

    owned_map: Dict[str, Dict[str, Any]] = {}
    for item in items:
        owned_map[item.item_id] = {
            "item_id": item.item_id,
            "owned": item.owned,
            "date_obtained": item.date_obtained,
            "notes": item.notes,
        }

    return {
        "user_id": current_user.id,
        "owned_item_ids": list(owned_map.keys()),
        "items": owned_map,
    }

@router.post("/toggle/{item_id}", response_model=CollectionItemResponse)
def toggle_item_owned(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify catalogue item exists
    cat_item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
    if not cat_item:
        raise HTTPException(status_code=404, detail="Catalogue item not found")

    if cat_item.category == "cp_wallets":
        raise HTTPException(
            status_code=400,
            detail="CP Wallets are automatically unlocked based on your total Collection Points and cannot be manually toggled."
        )

    record = db.query(UserCollectionItem).filter(
        UserCollectionItem.user_id == current_user.id,
        UserCollectionItem.item_id == item_id
    ).first()

    if record:
        record.owned = not record.owned
    else:
        record = UserCollectionItem(
            user_id=current_user.id,
            item_id=item_id,
            owned=True,
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    # Immediately recalculate and update CP wallet ownership
    sync_user_cp_wallet(current_user.id, db)

    return CollectionItemResponse(
        item_id=record.item_id,
        owned=record.owned,
        date_obtained=record.date_obtained or "",
        notes=record.notes or "",
    )

@router.put("/items/{item_id}", response_model=CollectionItemResponse)
def update_collection_item(
    item_id: str,
    req: CollectionItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat_item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
    if not cat_item:
        raise HTTPException(status_code=404, detail="Catalogue item not found")

    if cat_item.category == "cp_wallets":
        raise HTTPException(
            status_code=400,
            detail="CP Wallets are automatically unlocked based on your total Collection Points and cannot be manually edited."
        )

    record = db.query(UserCollectionItem).filter(
        UserCollectionItem.user_id == current_user.id,
        UserCollectionItem.item_id == item_id
    ).first()

    if record:
        record.owned = req.owned
        if req.date_obtained is not None:
            record.date_obtained = req.date_obtained
        if req.notes is not None:
            record.notes = req.notes
    else:
        record = UserCollectionItem(
            user_id=current_user.id,
            item_id=item_id,
            owned=req.owned,
            date_obtained=req.date_obtained or "",
            notes=req.notes or "",
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    # Immediately recalculate and update CP wallet ownership
    sync_user_cp_wallet(current_user.id, db)

    return CollectionItemResponse(
        item_id=record.item_id,
        owned=record.owned,
        date_obtained=record.date_obtained or "",
        notes=record.notes or "",
    )

@router.get("/stats", response_model=CPStatsResponse)
def get_collection_cp_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure active CP tier wallet is synchronized
    sync_user_cp_wallet(current_user.id, db)

    # Fetch all catalogue items
    all_items = db.query(CatalogueItem).all()
    # Fetch user's owned records
    user_owned_ids = set(
        r[0] for r in db.query(UserCollectionItem.item_id).filter(
            UserCollectionItem.user_id == current_user.id,
            UserCollectionItem.owned == True
        ).all()
    )

    # Fetch user's gem selections
    user_gems = db.query(UserGem).filter(UserGem.user_id == current_user.id).all()
    user_gem_levels = {ug.item_id: ug.current_level for ug in user_gems}

    # Categories contributing to CP: skins, frames, nameplates, wallets, stickers, speech_bubbles
    standard_cp_categories = {"skins", "frames", "nameplates", "wallets", "stickers", "speech_bubbles"}

    category_breakdown = {
        "skins": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "icons": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "cards": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "wallets": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "cp_wallets": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "nameplates": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "frames": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "gems": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "stickers": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "speech_bubbles": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "postcards": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "refinements": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
    }

    total_cp = 0
    user_cp = 0
    total_items = 0
    owned_items = 0

    for item in all_items:
        cat = item.category.lower()
        if cat not in category_breakdown:
            category_breakdown[cat] = {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0}

        category_breakdown[cat]["total"] += 1

        if cat == "gems":
            # For gems, each gem max CP is 1099 (Level 16)
            gem_max_cp = 1099
            category_breakdown[cat]["max_cp"] += gem_max_cp
            total_cp += gem_max_cp

            current_lvl = user_gem_levels.get(item.id, 0)
            if current_lvl > 0:
                gem_user_cp = GEM_LEVEL_CP_MAP.get(current_lvl, (0, 0))[0]
                category_breakdown[cat]["owned"] += 1
                category_breakdown[cat]["user_cp"] += gem_user_cp
                user_cp += gem_user_cp
                owned_items += 1
            total_items += 1
        else:
            is_owned = item.id in user_owned_ids
            item_cp = int(item.cp or 0)

            if is_owned:
                category_breakdown[cat]["owned"] += 1

            if cat in standard_cp_categories:
                category_breakdown[cat]["max_cp"] += item_cp
                total_cp += item_cp
                if is_owned:
                    category_breakdown[cat]["user_cp"] += item_cp
                    user_cp += item_cp

            # Cards are excluded from total_items count in original Mafia42 journal
            if cat != "cards":
                total_items += 1
                if is_owned:
                    owned_items += 1

    completion_percentage = (user_cp / total_cp * 100) if total_cp > 0 else 0.0

    return CPStatsResponse(
        total_cp=total_cp,
        user_cp=user_cp,
        completion_percentage=round(completion_percentage, 2),
        category_breakdown=category_breakdown,
        total_items=total_items,
        owned_items=owned_items,
    )

