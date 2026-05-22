"""Signup, login, and current-user routes."""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.auth_utils import (
    create_access_token,
    get_current_user_dep,
    get_db_dep,
    hash_password,
    verify_password,
)
from backend.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("Invalid email address")
    return email


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _normalize_email(v)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _normalize_email(v)


class UserPublic(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


def build_auth_router(
    session_factory: sessionmaker,
    *,
    jwt_secret: str,
    jwt_expire_minutes: int,
) -> APIRouter:
    get_db = get_db_dep(session_factory)
    get_current_user = get_current_user_dep(session_factory, jwt_secret)

    @router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    def signup(body: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
        email = body.email
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(body.password),
            first_name=body.first_name.strip(),
            last_name=body.last_name.strip(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(
            subject=str(user.id),
            secret=jwt_secret,
            expires_minutes=jwt_expire_minutes,
        )
        return AuthResponse(access_token=token, user=UserPublic.model_validate(user))

    @router.post("/login", response_model=AuthResponse)
    def login(body: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
        email = body.email
        user = db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(
            subject=str(user.id),
            secret=jwt_secret,
            expires_minutes=jwt_expire_minutes,
        )
        return AuthResponse(access_token=token, user=UserPublic.model_validate(user))

    @router.get("/me", response_model=UserPublic)
    def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
        return UserPublic.model_validate(current_user)

    return router
