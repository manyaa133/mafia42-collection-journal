import os
import uuid
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models import User, CatalogueItem, UserCollectionItem, AuditLog
from backend.app.schemas import (
    CatalogueItemCreate, CatalogueItemUpdate, CatalogueItemResponse,
    CatalogueReorderRequest, CatalogueItemMoveRequest, CatalogueImportRequest,
    UserAdminView, UserStatusUpdate, AuditLogResponse
)
from backend.app.auth import get_current_owner

router = APIRouter(prefix="/admin", tags=["Owner Administration"])

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_ASSETS = os.path.join(WORKSPACE_DIR, "backend", "static", "assets")
FRONTEND_ASSETS = os.path.join(WORKSPACE_DIR, "frontend", "public", "assets")

# Catalogue Management
@router.post("/catalogue", response_model=CatalogueItemResponse)
def create_catalogue_item(
    req: CatalogueItemCreate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    item_id = req.id or f"m42_{req.category.lower()}_{uuid.uuid4().hex[:8]}"
    existing = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="An item with this ID already exists")

    new_item = CatalogueItem(
        id=item_id,
        category=req.category.lower().strip(),
        name=req.name,
        character=req.character or "",
        card_id=req.card_id or "",
        rarity=req.rarity or "",
        level=req.level or 1,
        cp=req.cp or 0,
        description=req.description or "",
        condition=req.condition or "",
        how_to=req.how_to or "",
        extra=req.extra or "",
        image=req.image or "",
        logo_image=req.logo_image or "",
        wallet_images=req.wallet_images or [],
        display_order=req.display_order or 0,
    )
    db.add(new_item)

    audit = AuditLog(
        user_id=owner.id,
        action="CATALOGUE_ITEM_CREATE",
        target_type="catalogue_item",
        target_id=item_id,
        details=f"Created {req.category} item: {req.name} ({item_id}) with {req.cp} CP",
    )
    db.add(audit)
    db.commit()
    db.refresh(new_item)
    return CatalogueItemResponse.model_validate(new_item)

@router.put("/catalogue/{item_id}", response_model=CatalogueItemResponse)
def update_catalogue_item(
    item_id: str,
    req: CatalogueItemUpdate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Catalogue item not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and isinstance(value, str):
            value = value.lower().strip()
        setattr(item, field, value)

    audit = AuditLog(
        user_id=owner.id,
        action="CATALOGUE_ITEM_UPDATE",
        target_type="catalogue_item",
        target_id=item_id,
        details=f"Updated item: {item.name} ({item_id})",
    )
    db.add(audit)
    db.commit()
    db.refresh(item)
    return CatalogueItemResponse.model_validate(item)

@router.delete("/catalogue/{item_id}")
def delete_catalogue_item(
    item_id: str,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Catalogue item not found")

    item_name = item.name
    category = item.category

    # If deleting a card, safely unlink card_id from skins instead of deleting them!
    if category.lower() == "cards":
        db.query(CatalogueItem).filter(CatalogueItem.card_id == item_id).update({"card_id": ""})

    db.delete(item)

    audit = AuditLog(
        user_id=owner.id,
        action="CATALOGUE_ITEM_DELETE",
        target_type="catalogue_item",
        target_id=item_id,
        details=f"Deleted {category} item: {item_name} ({item_id})",
    )
    db.add(audit)
    db.commit()
    return {"message": f"Item {item_id} deleted successfully"}

@router.post("/catalogue/move")
def move_catalogue_item(
    req: CatalogueItemMoveRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    cat = req.category.lower().strip()
    items = db.query(CatalogueItem).filter(CatalogueItem.category == cat).order_by(CatalogueItem.display_order.asc(), CatalogueItem.id.asc()).all()

    item_index = -1
    for idx, it in enumerate(items):
        if it.id == req.item_id:
            item_index = idx
            break

    if item_index == -1:
        raise HTTPException(status_code=404, detail=f"Item {req.item_id} not found in category {cat}")

    target_index = item_index
    if req.direction:
        d = req.direction.lower().strip()
        if d in ("up", "left", "prev"):
            target_index = max(0, item_index - 1)
        elif d in ("down", "right", "next"):
            target_index = min(len(items) - 1, item_index + 1)
        else:
            raise HTTPException(status_code=400, detail="Invalid direction. Use 'up'/'left'/'prev' or 'down'/'right'/'next'")
    elif req.target_position is not None:
        target_index = max(0, min(len(items) - 1, req.target_position - 1))
    else:
        raise HTTPException(status_code=400, detail="Specify either 'direction' or 'target_position'")

    if target_index != item_index:
        moved = items.pop(item_index)
        items.insert(target_index, moved)
        for i, it in enumerate(items):
            it.display_order = i

        audit = AuditLog(
            user_id=owner.id,
            action="CATALOGUE_ITEM_MOVE",
            target_type="catalogue_item",
            target_id=req.item_id,
            details=f"Moved {cat} item {moved.name} ({req.item_id}) from position {item_index + 1} to {target_index + 1}",
        )
        db.add(audit)
        db.commit()

    return {
        "message": f"Item {req.item_id} successfully moved to position {target_index + 1}",
        "item_id": req.item_id,
        "new_position": target_index + 1,
        "total_items": len(items)
    }

@router.post("/catalogue/reorder")
def reorder_catalogue_items(
    req: CatalogueReorderRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    for index, item_id in enumerate(req.item_ids):
        item = db.query(CatalogueItem).filter(
            CatalogueItem.id == item_id,
            CatalogueItem.category == req.category.lower()
        ).first()
        if item:
            item.display_order = index

    audit = AuditLog(
        user_id=owner.id,
        action="CATALOGUE_REORDER",
        target_type="category",
        target_id=req.category,
        details=f"Reordered {len(req.item_ids)} items in category {req.category}",
    )
    db.add(audit)
    db.commit()
    return {"message": "Items reordered successfully"}

@router.post("/catalogue/import")
def import_catalogue(
    req: CatalogueImportRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    imported_count = 0
    for cat, cat_items in req.data.items():
        for idx, item_data in enumerate(cat_items):
            item_id = item_data.get("id")
            if not item_id:
                continue
            existing = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
            if existing:
                for field in ["name", "character", "card_id", "rarity", "level", "cp", "description", "condition", "how_to", "extra", "image", "logo_image"]:
                    if field in item_data:
                        setattr(existing, field, item_data[field])
                if "display_order" in item_data:
                    existing.display_order = item_data["display_order"]
            else:
                new_item = CatalogueItem(
                    id=item_id,
                    category=cat.lower(),
                    name=item_data.get("name", ""),
                    character=item_data.get("character", ""),
                    card_id=item_data.get("card_id", ""),
                    rarity=item_data.get("rarity", ""),
                    level=item_data.get("level", 1),
                    cp=item_data.get("cp", 0),
                    description=item_data.get("description", ""),
                    condition=item_data.get("condition", ""),
                    how_to=item_data.get("how_to", ""),
                    extra=item_data.get("extra", ""),
                    image=item_data.get("image", ""),
                    logo_image=item_data.get("logo_image", ""),
                    wallet_images=item_data.get("wallet_images", []),
                    display_order=item_data.get("display_order", idx),
                )
                db.add(new_item)
            imported_count += 1

    audit = AuditLog(
        user_id=owner.id,
        action="CATALOGUE_IMPORT",
        target_type="catalogue",
        target_id="all",
        details=f"Imported/updated {imported_count} catalogue items preserving display_order",
    )
    db.add(audit)
    db.commit()
    return {"message": f"Successfully imported {imported_count} catalogue items", "count": imported_count}

@router.post("/upload-image")
async def upload_catalogue_image(
    file: UploadFile = File(...),
    category: str = Form("general"),
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    cat_clean = category.lower().strip()
    allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Invalid image file format. Allowed: png, jpg, webp, gif")

    target_filename = f"{cat_clean}_{uuid.uuid4().hex[:12]}{ext}"
    target_backend_dir = os.path.join(BACKEND_ASSETS, cat_clean)
    target_frontend_dir = os.path.join(FRONTEND_ASSETS, cat_clean)
    os.makedirs(target_backend_dir, exist_ok=True)
    os.makedirs(target_frontend_dir, exist_ok=True)

    dest_backend = os.path.join(target_backend_dir, target_filename)
    dest_frontend = os.path.join(target_frontend_dir, target_filename)

    with open(dest_backend, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        shutil.copyfile(dest_backend, dest_frontend)
    except Exception:
        pass

    url = f"/assets/{cat_clean}/{target_filename}"

    audit = AuditLog(
        user_id=owner.id,
        action="IMAGE_UPLOAD",
        target_type="asset",
        target_id=target_filename,
        details=f"Uploaded image to {url} ({len(content)} bytes)",
    )
    db.add(audit)
    db.commit()

    return {"url": url, "filename": target_filename}

# User Management
@router.get("/users", response_model=List[UserAdminView])
def get_all_users(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    results = []
    for u in users:
        owned_count = db.query(UserCollectionItem).filter(
            UserCollectionItem.user_id == u.id,
            UserCollectionItem.owned == True
        ).count()
        results.append(UserAdminView(
            id=u.id,
            email=u.email,
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            owned_items_count=owned_count,
        ))
    return results

@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    req: UserStatusUpdate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.id == owner.id:
        raise HTTPException(status_code=400, detail="Owner cannot suspend their own account")

    target_user.is_active = req.is_active
    action_name = "ENABLE_USER" if req.is_active else "SUSPEND_USER"
    audit = AuditLog(
        user_id=owner.id,
        action=action_name,
        target_type="user",
        target_id=user_id,
        details=f"User {target_user.username} is_active set to {req.is_active}",
    )
    db.add(audit)
    db.commit()
    return {"message": f"User status updated to {'active' if req.is_active else 'suspended'}"}

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [AuditLogResponse.model_validate(l) for l in logs]

# Export / Import Catalogue
@router.get("/catalogue/export")
def export_catalogue(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    items = db.query(CatalogueItem).order_by(CatalogueItem.display_order.asc()).all()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for i in items:
        cat = i.category.lower()
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "id": i.id,
            "category": i.category,
            "name": i.name,
            "character": i.character,
            "card_id": i.card_id,
            "rarity": i.rarity,
            "level": i.level,
            "cp": i.cp,
            "description": i.description,
            "condition": i.condition,
            "how_to": i.how_to,
            "extra": i.extra,
            "image": i.image,
            "logo_image": i.logo_image,
            "wallet_images": i.wallet_images,
            "display_order": i.display_order,
        })

    return {
        "app": "Mafia42 Collection Journal",
        "formatVersion": 2,
        "exportedAt": datetime.utcnow().isoformat(),
        "exportedBy": owner.username,
        "data": grouped,
    }

