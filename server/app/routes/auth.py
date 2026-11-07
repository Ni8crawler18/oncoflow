from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import RegisterRequest, LoginRequest, AuthResponse, UserOut
from ..security import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(401, "Not authenticated")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "User no longer exists")
    return user


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "A valid email is required")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")

    user = User(
        name=payload.name.strip() or "Clinician",
        email=email,
        password_hash=hash_password(payload.password),
        specialty=payload.specialty,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id, user.email), user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return AuthResponse(token=create_token(user.id, user.email), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
