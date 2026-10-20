from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import CatalogueItem
from backend.app.schemas import CatalogueItemResponse

router = APIRouter(prefix="/catalogue", tags=["Shared Catalogue"])

@router.get("", response_model=Dict[str, List[CatalogueItemResponse]])
def get_all_catalogue_items(
    search: Optional[str] = Query(None, description="Search by name or character"),
    db: Session = Depends(get_db)
):
    query = db.query(CatalogueItem).order_by(CatalogueItem.display_order.asc(), CatalogueItem.name.asc())
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(CatalogueItem.name.ilike(s), CatalogueItem.character.ilike(s)))
    
    items = query.all()
    grouped: Dict[str, List[CatalogueItemResponse]] = {
        "cards": [],
        "skins": [],
        "icons": [],
        "frames": [],
        "nameplates": [],
        "wallets": [],
        "cp_wallets": [],
        "gems": [],
        "stickers": [],
        "speech_bubbles": [],
        "postcards": [],
        "refinements": [],
    }

    for item in items:
        cat = (item.category or "").lower().strip()
        if cat in grouped:
            grouped[cat].append(CatalogueItemResponse.model_validate(item))
        else:
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(CatalogueItemResponse.model_validate(item))

    return grouped

@router.get("/{category}", response_model=List[CatalogueItemResponse])
def get_catalogue_by_category(
    category: str,
    search: Optional[str] = Query(None),
    character: Optional[str] = Query(None),
    rarity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(CatalogueItem).filter(CatalogueItem.category == category.lower())
    
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(CatalogueItem.name.ilike(s), CatalogueItem.character.ilike(s)))
    if character:
        query = query.filter(CatalogueItem.character.ilike(f"%{character.strip()}%"))
    if rarity:
        query = query.filter(CatalogueItem.rarity.ilike(rarity.strip()))

    items = query.order_by(CatalogueItem.display_order.asc(), CatalogueItem.name.asc()).all()
    return [CatalogueItemResponse.model_validate(i) for i in items]

@router.get("/cards/{card_id}/skins", response_model=List[CatalogueItemResponse])
def get_card_associated_skins(card_id: str, db: Session = Depends(get_db)):
    card = db.query(CatalogueItem).filter(
        CatalogueItem.category == "cards",
        CatalogueItem.id == card_id
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    skins = db.query(CatalogueItem).filter(
        CatalogueItem.category == "skins",
        or_(
            CatalogueItem.card_id == card_id,
            (CatalogueItem.card_id == "") & (CatalogueItem.character == card.name) & (card.name != "None")
        )
    ).order_by(CatalogueItem.display_order.asc(), CatalogueItem.name.asc()).all()

    return [CatalogueItemResponse.model_validate(s) for s in skins]

@router.get("/skins/{skin_id}/card", response_model=Optional[CatalogueItemResponse])
def get_skin_associated_card(skin_id: str, db: Session = Depends(get_db)):
    skin = db.query(CatalogueItem).filter(
        CatalogueItem.category == "skins",
        CatalogueItem.id == skin_id
    ).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found")

    card = None
    if skin.card_id:
        card = db.query(CatalogueItem).filter(
            CatalogueItem.category == "cards",
            CatalogueItem.id == skin.card_id
        ).first()
    if not card and skin.character and skin.character != "None":
        card = db.query(CatalogueItem).filter(
            CatalogueItem.category == "cards",
            CatalogueItem.name == skin.character
        ).first()

    return CatalogueItemResponse.model_validate(card) if card else None

@router.get("/{category}/{item_id}", response_model=CatalogueItemResponse)
def get_catalogue_item(category: str, item_id: str, db: Session = Depends(get_db)):
    item = db.query(CatalogueItem).filter(
        CatalogueItem.category == category.lower(),
        CatalogueItem.id == item_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Catalogue item not found")
    return CatalogueItemResponse.model_validate(item)

