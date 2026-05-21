import hashlib
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import AppUser, UserSession


def hash_access_token(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header.")

    return token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AppUser:
    access_token = _extract_bearer_token(authorization)
    token_hash = hash_access_token(access_token)
    statement = (
        select(UserSession)
        .where(UserSession.token_hash == token_hash)
        .where(UserSession.expires_at > datetime.now(timezone.utc))
    )
    user_session = db.scalar(statement)
    if user_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")

    user = db.get(AppUser, user_session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session user.")

    return user


def get_current_access_token(authorization: str | None = Header(default=None)) -> str:
    return _extract_bearer_token(authorization)
