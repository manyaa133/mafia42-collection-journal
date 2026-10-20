import os
import json
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

# Resolve workspace root (three dirs up from routers: backend/app/routers/admin.py -> workspace)
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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


# ===========================================================================
# MANUAL IMAGE REPLACEMENT APPROVAL SYSTEM
# ===========================================================================
PROPOSALS_PATH = os.path.join(WORKSPACE_DIR, "database", "proposed_image_replacements.json")
DECISIONS_PATH = os.path.join(WORKSPACE_DIR, "database", "image_review_decisions.json")
SEED_CATALOGUE_PATH = os.path.join(WORKSPACE_DIR, "database", "seed_catalogue.json")
SEED_GEMS_PATH = os.path.join(WORKSPACE_DIR, "database", "seed_gems.json")

def load_decisions() -> dict:
    data = {"decisions": {}, "rejected_history": {}}
    if os.path.exists(DECISIONS_PATH):
        try:
            with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    if "decisions" not in data:
        data["decisions"] = {}
    if "rejected_history" not in data:
        data["rejected_history"] = {}
        for iid, dec in data["decisions"].items():
            if dec.get("action") == "rejected" and dec.get("proposed_url"):
                data["rejected_history"].setdefault(iid, []).append(dec.get("proposed_url"))
    return data

def save_decisions(data: dict):
    with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_proposal_status(prop: dict, decisions_data: dict) -> str:
    item_id = prop["id"]
    decisions = decisions_data.get("decisions", {})
    decision = decisions.get(item_id)
    
    if decision:
        act = decision.get("action")
        if act in ("approved", "rejected"):
            return act
        
    return "pending"

ALL_REVIEW_CATEGORIES = [
    "cards",
    "card_logos",
    "skin_main",
    "skin_logo",
    "frames",
    "nameplates",
    "icons",
    "gems",
]

@router.get("/image-proposals")
def get_image_proposals(
    category: Optional[str] = None,
    status_filter: Optional[str] = "pending",
    db: Session = Depends(get_db)
):
    if not os.path.exists(PROPOSALS_PATH):
        return {"proposals": [], "total": 0}
    
    with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
        all_proposals = json.load(f)
        
    decisions_data = load_decisions()
    decisions = decisions_data.get("decisions", {})
    
    result = []
    cat_req = category.lower() if category else None
    if cat_req == "skins":
        cats_to_check = ["skin_main", "skin_logo"]
    elif cat_req and cat_req != "all":
        cats_to_check = [cat_req]
    else:
        cats_to_check = ALL_REVIEW_CATEGORIES
    
    # Load gems seed for live gem level image lookups
    gems_seed_dict = {}
    if os.path.exists(SEED_GEMS_PATH):
        try:
            with open(SEED_GEMS_PATH, "r", encoding="utf-8") as gf:
                for g in json.load(gf):
                    rid = g.get("role_id")
                    for lv in g.get("levels", []):
                        gems_seed_dict[(rid, lv.get("level"))] = lv.get("image")
        except Exception:
            pass

    skin_batch_cache = {}
    for cat in cats_to_check:
        for prop in all_proposals.get(cat, []):
            item_id = prop["id"]
            decision = decisions.get(item_id)
            current_status = get_proposal_status(prop, decisions_data)
            
            # Update current image dynamically from database/seed if possible
            if cat == "card_logos":
                card_id = prop.get("card_id") or item_id.replace("card_logo_", "")
                db_item = db.query(CatalogueItem).filter(CatalogueItem.id == card_id).first()
                if db_item and db_item.logo_image:
                    prop["current_image"] = db_item.logo_image
            elif cat == "skin_main":
                skin_id = prop.get("skin_id") or item_id.replace("skin_main_", "")
                db_item = db.query(CatalogueItem).filter(CatalogueItem.id == skin_id).first()
                if db_item and db_item.image:
                    prop["current_image"] = db_item.image
            elif cat == "skin_logo":
                skin_id = prop.get("skin_id") or item_id.replace("skin_logo_", "")
                db_item = db.query(CatalogueItem).filter(CatalogueItem.id == skin_id).first()
                if db_item and db_item.logo_image:
                    prop["current_image"] = db_item.logo_image
            elif cat == "gems":
                role_id = prop.get("role_id")
                level = prop.get("level")
                if (role_id, level) in gems_seed_dict:
                    prop["current_image"] = gems_seed_dict[(role_id, level)]
            else:
                db_item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
                if db_item:
                    prop["current_image"] = db_item.image
                    prop["current_logo"] = db_item.logo_image
                
            prop_copy = dict(prop)
            prop_copy["status"] = current_status
            prop_copy["decision_details"] = decision

            # Ensure all pending or rejected skins/logos get the full 20 candidates of the active batch
            if cat in ("skin_main", "skin_logo") and current_status in ("pending", "rejected"):
                if cat not in skin_batch_cache:
                    from backend.scripts.manage_skin_batches import load_batch_state
                    b_state = load_batch_state(cat)
                    skin_batch_cache[cat] = b_state.get("current_batch", [])
                active_cands = skin_batch_cache[cat]
                if active_cands:
                    prop_copy["candidates"] = active_cands
                    if not prop_copy.get("proposed_url") or prop_copy.get("proposed_url") not in [c["url"] for c in active_cands]:
                        prop_copy["proposed_url"] = active_cands[0]["url"]
                        prop_copy["proposed_repo_path"] = active_cands[0]["repo_path"]
            
            if status_filter == "all":
                result.append(prop_copy)
            elif status_filter == "unresolved":
                if current_status in ("pending", "rejected"):
                    result.append(prop_copy)
            elif current_status == status_filter:
                result.append(prop_copy)
                
    return {"proposals": result, "total": len(result)}

@router.get("/image-proposals/summary")
def get_image_proposals_summary():
    if not os.path.exists(PROPOSALS_PATH):
        return {"summary": {}}
    with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
        all_proposals = json.load(f)
    decisions_data = load_decisions()
    
    summary = {}
    for cat in ALL_REVIEW_CATEGORIES:
        items = all_proposals.get(cat, [])
        pending = sum(1 for it in items if get_proposal_status(it, decisions_data) == "pending")
        approved = sum(1 for it in items if get_proposal_status(it, decisions_data) == "approved")
        rejected = sum(1 for it in items if get_proposal_status(it, decisions_data) == "rejected")
        summary[cat] = {
            "total": len(items),
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }
    return {"summary": summary}

@router.post("/image-proposals/review")
def review_image_proposal(
    req: dict,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    item_id = req.get("item_id")
    action = req.get("action") # approve | reject | skip
    category = req.get("category", "").lower()
    proposed_url = req.get("proposed_url")
    proposed_logo_url = req.get("proposed_logo_url")
    target_field = req.get("target_field")
    
    if not item_id or action not in ("approve", "reject", "skip"):
        raise HTTPException(status_code=400, detail="Invalid request parameters")
        
    decisions_data = load_decisions()
    
    if action == "skip":
        return {"message": f"Proposal for {item_id} skipped."}
        
    # Record decision
    if "rejected_history" not in decisions_data:
        decisions_data["rejected_history"] = {}
        
    if action == "reject":
        history = decisions_data["rejected_history"].setdefault(item_id, [])
        if proposed_url and proposed_url not in history:
            history.append(proposed_url)
        if proposed_logo_url and proposed_logo_url not in history:
            history.append(proposed_logo_url)
            
        # If rejecting a skin or logo, immediately attach the full active 20-candidate batch to this proposal
        if category in ("skin_main", "skin_logo") or item_id.startswith(("skin_main_", "skin_logo_")):
            cat_key = "skin_main" if ("skin_main" in category or item_id.startswith("skin_main_")) else "skin_logo"
            from backend.scripts.manage_skin_batches import load_batch_state
            b_state = load_batch_state(cat_key)
            active_batch = b_state.get("current_batch", [])
            if active_batch and os.path.exists(PROPOSALS_PATH):
                try:
                    with open(PROPOSALS_PATH, "r", encoding="utf-8") as pf:
                        all_props = json.load(pf)
                    for p in all_props.get(cat_key, []):
                        if p.get("id") == item_id:
                            p["candidates"] = active_batch
                            p["proposed_url"] = active_batch[0]["url"]
                            p["proposed_repo_path"] = active_batch[0]["repo_path"]
                            p["batch_number"] = b_state.get("current_batch_number", 1)
                    with open(PROPOSALS_PATH, "w", encoding="utf-8") as pf:
                        json.dump(all_props, pf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print("Error updating proposal candidates on reject:", e)
            
    decisions_data["decisions"][item_id] = {
        "action": "approved" if action == "approve" else "rejected",
        "item_id": item_id,
        "category": category,
        "proposed_url": proposed_url,
        "proposed_logo_url": proposed_logo_url,
        "target_field": target_field,
        "reviewed_by": owner.username,
        "timestamp": datetime.utcnow().isoformat()
    }
    save_decisions(decisions_data)
    
    # If approved, update ONLY this specific catalogue item and designated field
    if action == "approve":
        # 1. Card Logos
        if category == "card_logos":
            card_id = req.get("card_id") or item_id.replace("card_logo_", "")
            db_item = db.query(CatalogueItem).filter(CatalogueItem.id == card_id).first()
            if db_item and proposed_url:
                db_item.logo_image = proposed_url
                db.commit()

            if os.path.exists(SEED_CATALOGUE_PATH):
                with open(SEED_CATALOGUE_PATH, "r", encoding="utf-8") as f:
                    cat_file = json.load(f)
                for item in cat_file.get("cards", []):
                    if item.get("id") == card_id:
                        if proposed_url:
                            item["logo_image"] = proposed_url
                with open(SEED_CATALOGUE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cat_file, f, indent=2, ensure_ascii=False)

            audit = AuditLog(
                user_id=owner.id,
                action="MANUAL_IMAGE_APPROVED",
                target_type="catalogue_item",
                target_id=card_id,
                details=f"Owner approved replacement logo for card {card_id}: {proposed_url}"
            )
            db.add(audit)
            db.commit()
            return {"message": f"Successfully approved logo for card {card_id}", "status": "approved"}

        # 2. Skin Main Images (Artwork only!)
        elif category == "skin_main":
            skin_id = req.get("skin_id") or item_id.replace("skin_main_", "")
            db_item = db.query(CatalogueItem).filter(CatalogueItem.id == skin_id).first()
            if db_item and proposed_url:
                db_item.image = proposed_url
                db.commit()

            if os.path.exists(SEED_CATALOGUE_PATH):
                with open(SEED_CATALOGUE_PATH, "r", encoding="utf-8") as f:
                    cat_file = json.load(f)
                for item in cat_file.get("skins", []):
                    if item.get("id") == skin_id:
                        if proposed_url:
                            item["image"] = proposed_url
                with open(SEED_CATALOGUE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cat_file, f, indent=2, ensure_ascii=False)

            audit = AuditLog(
                user_id=owner.id,
                action="MANUAL_IMAGE_APPROVED",
                target_type="catalogue_item",
                target_id=skin_id,
                details=f"Owner approved main artwork for skin {skin_id}: {proposed_url}"
            )
            db.add(audit)
            db.commit()
            return {"message": f"Successfully approved main image for skin {skin_id}", "status": "approved"}

        # 3. Skin Logos (Logo badge only!)
        elif category == "skin_logo":
            skin_id = req.get("skin_id") or item_id.replace("skin_logo_", "")
            target_logo = proposed_logo_url or proposed_url
            db_item = db.query(CatalogueItem).filter(CatalogueItem.id == skin_id).first()
            if db_item and target_logo:
                db_item.logo_image = target_logo
                db.commit()

            if os.path.exists(SEED_CATALOGUE_PATH):
                with open(SEED_CATALOGUE_PATH, "r", encoding="utf-8") as f:
                    cat_file = json.load(f)
                for item in cat_file.get("skins", []):
                    if item.get("id") == skin_id:
                        if target_logo:
                            item["logo_image"] = target_logo
                            item["logoImage"] = target_logo
                with open(SEED_CATALOGUE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cat_file, f, indent=2, ensure_ascii=False)

            audit = AuditLog(
                user_id=owner.id,
                action="MANUAL_IMAGE_APPROVED",
                target_type="catalogue_item",
                target_id=skin_id,
                details=f"Owner approved logo for skin {skin_id}: {proposed_url}"
            )
            db.add(audit)
            db.commit()
            return {"message": f"Successfully approved logo for skin {skin_id}", "status": "approved"}

        # 4. Gems (Specific role and level!)
        elif category == "gems":
            role_id = req.get("role_id")
            level = req.get("level")
            if not role_id or not level:
                # Try parsing from item_id: gem_{role}_lv{level}
                parts = item_id.replace("gem_", "").split("_lv")
                if len(parts) == 2:
                    role_id = parts[0]
                    try:
                        level = int(parts[1])
                    except ValueError:
                        level = 16

            if os.path.exists(SEED_GEMS_PATH):
                with open(SEED_GEMS_PATH, "r", encoding="utf-8") as f:
                    gems_list = json.load(f)
                for g in gems_list:
                    if g.get("role_id") == role_id:
                        for lv in g.get("levels", []):
                            if lv.get("level") == level:
                                if proposed_url:
                                    lv["image"] = proposed_url
                        if level == 16 and proposed_url:
                            g["image"] = proposed_url
                with open(SEED_GEMS_PATH, "w", encoding="utf-8") as f:
                    json.dump(gems_list, f, indent=2, ensure_ascii=False)

            if level == 16:
                db_gem = db.query(CatalogueItem).filter(CatalogueItem.id == f"gem_{role_id}").first()
                if db_gem and proposed_url:
                    db_gem.image = proposed_url
                    db.commit()

            audit = AuditLog(
                user_id=owner.id,
                action="MANUAL_IMAGE_APPROVED",
                target_type="gem_level",
                target_id=item_id,
                details=f"Owner approved image for {role_id} gem level {level}: {proposed_url}"
            )
            db.add(audit)
            db.commit()
            return {"message": f"Successfully approved gem level {level} for {role_id}", "status": "approved"}

        # 5. Standard catalogue items (Cards, Frames, Nameplates, Icons)
        db_item = db.query(CatalogueItem).filter(CatalogueItem.id == item_id).first()
        if db_item and proposed_url:
            db_item.image = proposed_url
            db.commit()

        target_cat = category if category in ("cards", "frames", "nameplates", "icons") else None
        if target_cat and os.path.exists(SEED_CATALOGUE_PATH):
            with open(SEED_CATALOGUE_PATH, "r", encoding="utf-8") as f:
                cat_file = json.load(f)
            for item in cat_file.get(target_cat, []):
                if item.get("id") == item_id:
                    if proposed_url:
                        item["image"] = proposed_url
            with open(SEED_CATALOGUE_PATH, "w", encoding="utf-8") as f:
                json.dump(cat_file, f, indent=2, ensure_ascii=False)

        audit = AuditLog(
            user_id=owner.id,
            action="MANUAL_IMAGE_APPROVED",
            target_type="catalogue_item",
            target_id=item_id,
            details=f"Owner approved replacement image for {item_id}: {proposed_url}"
        )
        db.add(audit)
        db.commit()
        return {"message": f"Successfully approved image for {item_id}", "status": "approved"}
    else:
        # Rejected
        audit = AuditLog(
            user_id=owner.id,
            action="MANUAL_IMAGE_REJECTED",
            target_type="catalogue_item",
            target_id=item_id,
            details=f"Owner rejected proposed replacement for {item_id}"
        )
        db.add(audit)
        db.commit()
        return {"message": f"Successfully recorded rejection for {item_id}", "status": "rejected"}


# ===========================================================================
# SHARED FRAME BATCH MANAGEMENT ENDPOINTS
# ===========================================================================
@router.get("/frames/batch-status")
def get_frame_batch_status():
    from backend.scripts.manage_frame_batches import load_batch_state, load_assigned_assets
    state = load_batch_state()
    approved_fids, pending_frames, *rest = load_assigned_assets()
    return {
        "current_batch_number": state.get("current_batch_number", 1),
        "current_batch": state.get("current_batch", []),
        "pending_frames_count": len(pending_frames),
        "total_approved_frames": len(approved_fids),
        "presented_count": len(state.get("presented_history_hashes", []))
    }

@router.post("/frames/next-batch")
def post_frame_next_batch(owner: User = Depends(get_current_owner)):
    from backend.scripts.manage_frame_batches import advance_to_next_batch, load_batch_state, load_assigned_assets
    new_cands = advance_to_next_batch()
    state = load_batch_state()
    approved_fids, pending_frames, *rest = load_assigned_assets()
    return {
        "message": f"Successfully advanced to Batch #{state.get('current_batch_number')}",
        "current_batch_number": state.get("current_batch_number"),
        "current_batch": new_cands,
        "pending_frames_count": len(pending_frames)
    }


# ===========================================================================
# SHARED SKIN BATCH MANAGEMENT ENDPOINTS (20 Candidates Per Batch)
# ===========================================================================
@router.get("/skins/batch-status")
def get_skin_batch_status(mode: str = "skin_main"):
    from backend.scripts.manage_skin_batches import load_batch_state, load_assigned_assets, init_or_get_batch_1
    state = load_batch_state(mode)
    if not state.get("current_batch"):
        init_or_get_batch_1(mode=mode, n=20)
        state = load_batch_state(mode)
    approved_ids, pending_skins, *rest = load_assigned_assets(mode)
    return {
        "mode": mode,
        "current_batch_number": state.get("current_batch_number", 1),
        "current_batch": state.get("current_batch", []),
        "pending_skins_count": len(pending_skins),
        "total_approved_skins": len(approved_ids),
        "presented_count": len(state.get("presented_history_hashes", [])),
        "available_batches": [b.get("batch_number") for b in state.get("batch_history", []) if b.get("candidates")]
    }

@router.post("/skins/next-batch")
def post_skin_next_batch(mode: str = "skin_main", owner: User = Depends(get_current_owner)):
    from backend.scripts.manage_skin_batches import advance_to_next_batch, load_batch_state, load_assigned_assets
    new_cands = advance_to_next_batch(mode=mode, n=20)
    state = load_batch_state(mode)
    approved_ids, pending_skins, *rest = load_assigned_assets(mode)
    return {
        "message": f"Successfully advanced to Batch #{state.get('current_batch_number')} for {mode}",
        "mode": mode,
        "current_batch_number": state.get("current_batch_number"),
        "current_batch": new_cands,
        "pending_skins_count": len(pending_skins),
        "available_batches": [b.get("batch_number") for b in state.get("batch_history", []) if b.get("candidates")]
    }

@router.post("/skins/switch-batch")
def post_skin_switch_batch(mode: str = "skin_main", batch_number: int = 1, owner: User = Depends(get_current_owner)):
    from backend.scripts.manage_skin_batches import switch_to_batch, load_batch_state, load_assigned_assets
    try:
        cands = switch_to_batch(batch_num=batch_number, mode=mode)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    state = load_batch_state(mode)
    approved_ids, pending_skins, *rest = load_assigned_assets(mode)
    return {
        "message": f"Switched to Batch #{batch_number} for {mode}",
        "mode": mode,
        "current_batch_number": batch_number,
        "current_batch": cands,
        "pending_skins_count": len(pending_skins),
        "available_batches": [b.get("batch_number") for b in state.get("batch_history", []) if b.get("candidates")]
    }

@router.post("/skins/init-batch")
def post_skin_init_batch(mode: str = "skin_main", force: bool = False, owner: User = Depends(get_current_owner)):
    from backend.scripts.manage_skin_batches import init_or_get_batch_1, load_batch_state, load_assigned_assets
    cands = init_or_get_batch_1(mode=mode, force_reselect=force, n=20)
    state = load_batch_state(mode)
    approved_ids, pending_skins, *rest = load_assigned_assets(mode)
    return {
        "message": f"Initialized Batch #{state.get('current_batch_number')} with {len(cands)} candidates for {mode}",
        "mode": mode,
        "current_batch_number": state.get("current_batch_number"),
        "current_batch": cands,
        "pending_skins_count": len(pending_skins),
        "available_batches": [b.get("batch_number") for b in state.get("batch_history", []) if b.get("candidates")]
    }



