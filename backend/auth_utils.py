"""Password hashing and JWT helpers."""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session, sessionmaker

from backend.models import User

bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    secret: str,
    expires_minutes: int,
    extra: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=[ALGORITHM])


def get_db_dep(session_factory: sessionmaker):
    def get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return get_db


def get_current_user_dep(session_factory: sessionmaker, jwt_secret: str):
    get_db = get_db_dep(session_factory)

    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> User:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = credentials.credentials
        try:
            payload = decode_token(token, jwt_secret)
            sub = payload.get("sub")
            if sub is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            user_id = int(sub)
        except (JWTError, ValueError) as e:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from e

        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    return get_current_user
