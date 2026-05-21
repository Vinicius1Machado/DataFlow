from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_access_token, get_current_user, hash_access_token
from app.db.session import get_db
from app.models.user import AppUser, UserSession
from app.schemas.auth import AuthCredentials, AuthResponse, RegisterCredentials, UserProfileUpdate, UserResponse
from app.services.password_service import PasswordService


router = APIRouter(prefix="/auth", tags=["auth"])
SESSION_TTL_DAYS = 7


def _create_session(db: Session, user: AppUser) -> str:
    access_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_access_token(access_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS),
        )
    )
    db.commit()
    return access_token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterCredentials, db: Session = Depends(get_db)) -> AuthResponse:
    password_service = PasswordService()
    user = AppUser(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        organization=payload.organization,
        role=payload.role,
        password_hash=password_service.hash_password(payload.password),
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.") from exc

    access_token = _create_session(db, user)
    return AuthResponse(access_token=access_token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(AppUser).where(AppUser.username == payload.username))
    if user is None or not PasswordService().verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    access_token = _create_session(db, user)
    return AuthResponse(access_token=access_token, user=user)


@router.get("/me", response_model=UserResponse)
def me(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> AppUser:
    current_user.full_name = payload.full_name
    current_user.email = payload.email
    current_user.organization = payload.organization
    current_user.role = payload.role

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/logout")
def logout(
    access_token: str = Depends(get_current_access_token),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
) -> dict[str, str]:
    token_hash = hash_access_token(access_token)
    user_session = db.scalar(
        select(UserSession)
        .where(UserSession.user_id == current_user.id)
        .where(UserSession.token_hash == token_hash)
    )
    if user_session is not None:
        db.delete(user_session)
        db.commit()

    return {"status": "ok"}
