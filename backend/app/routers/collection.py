from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, CatalogueItem, UserCollectionItem, UserGem
from backend.app.schemas import CollectionItemResponse, CollectionItemUpdate, CPStatsResponse
from backend.app.auth import get_current_user

router = APIRouter(prefix="/collection", tags=["Personal Collection"])

@router.get("", response_model=Dict[str, Any])
def get_user_collection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    # Fetch all catalogue items
    all_items = db.query(CatalogueItem).all()
    # Fetch user's owned records
    user_owned_ids = set(
        r[0] for r in db.query(UserCollectionItem.item_id).filter(
            UserCollectionItem.user_id == current_user.id,
            UserCollectionItem.owned == True
        ).all()
    )

    # Categories contributing to CP: skins, gems, frames, nameplates
    cp_categories = {"skins", "gems", "frames", "nameplates"}

    category_breakdown = {
        "skins": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "icons": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "cards": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "wallets": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "cp_wallets": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "nameplates": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "frames": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
        "gems": {"total": 0, "owned": 0, "max_cp": 0, "user_cp": 0},
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

        is_owned = item.id in user_owned_ids
        item_cp = int(item.cp or 0)

        category_breakdown[cat]["total"] += 1
        if is_owned:
            category_breakdown[cat]["owned"] += 1

        if cat in cp_categories:
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

