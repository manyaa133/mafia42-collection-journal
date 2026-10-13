from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import User, UserProfile, AuditLog
from backend.app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.app.auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register_user(req: RegisterRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    # Check if username or email already exists
    existing = db.query(User).filter(
        or_(User.email == req.email.lower(), User.username == req.username)
    ).first()
    if existing:
        if existing.email == req.email.lower():
            raise HTTPException(status_code=400, detail="Email is already registered")
        raise HTTPException(status_code=400, detail="Username is already taken")

    # Enforce role: ordinary users can NEVER select their own role
    user = User(
        email=req.email.lower(),
        username=req.username,
        hashed_password=get_password_hash(req.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name=user.username,
        joined_date="2026-10-11",
    )
    db.add(profile)

    audit = AuditLog(
        user_id=user.id,
        action="USER_REGISTRATION",
        target_type="user",
        target_id=user.id,
        details=f"New user registered: {user.username} ({user.email})",
        ip_address=request.client.host if request.client else "",
    )
    db.add(audit)
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie(
        key="m42_access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.post("/login", response_model=TokenResponse)
def login_user(req: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        or_(
            User.email == req.username_or_email.lower(),
            User.username == req.username_or_email,
        )
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended or disabled by the owner.",
        )

    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        target_type="user",
        target_id=user.id,
        details=f"User logged in: {user.username}",
        ip_address=request.client.host if request.client else "",
    )
    db.add(audit)
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie(
        key="m42_access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("m42_access_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user

