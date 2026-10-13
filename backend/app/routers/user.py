from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, UserProfile, UserGoal, UserNote, UserAchievement
from backend.app.schemas import (
    UserProfileResponse, UserProfileUpdate,
    GoalResponse, GoalCreate, GoalUpdate,
    NoteResponse, NoteCreate, NoteUpdate
)
from backend.app.auth import get_current_user

router = APIRouter(prefix="/user", tags=["User Profile & Personal Data"])

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id, display_name=current_user.username)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile

# Goals
@router.get("/goals", response_model=List[GoalResponse])
def get_user_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = db.query(UserGoal).filter(UserGoal.user_id == current_user.id).order_by(UserGoal.created_at.desc()).all()
    return goals

@router.post("/goals", response_model=GoalResponse)
def create_goal(req: GoalCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = UserGoal(
        user_id=current_user.id,
        title=req.title,
        description=req.description or "",
        current_val=req.current_val or 0,
        target_val=req.target_val or 1,
        completed=False,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal

@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: str, req: GoalUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(UserGoal).filter(UserGoal.id == goal_id, UserGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(goal, k, v)
    
    db.commit()
    db.refresh(goal)
    return goal

@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(UserGoal).filter(UserGoal.id == goal_id, UserGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted successfully"}

# Notes
@router.get("/notes", response_model=List[NoteResponse])
def get_user_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(UserNote).filter(UserNote.user_id == current_user.id).order_by(UserNote.created_at.desc()).all()
    return notes

@router.post("/notes", response_model=NoteResponse)
def create_note(req: NoteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = UserNote(
        user_id=current_user.id,
        title=req.title or "",
        content=req.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

@router.delete("/notes/{note_id}")
def delete_note(note_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(UserNote).filter(UserNote.id == note_id, UserNote.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully"}

