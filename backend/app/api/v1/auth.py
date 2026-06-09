"""Authentication endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)
from app.services import auth_service
from app.services.audit_service import write_audit

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(
    payload: SignupRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    resp = await auth_service.signup(db, payload)
    await write_audit(
        db,
        action="auth.signup",
        actor_user_id=resp.user.id,
        meta={"email": resp.user.email},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return resp


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    resp = await auth_service.login(db, payload)
    await write_audit(
        db,
        action="auth.login",
        actor_user_id=resp.user.id,
        meta={"email": resp.user.email},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return resp


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenPair:
    return await auth_service.refresh(db, payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    await auth_service.logout(db, payload.refresh_token)
