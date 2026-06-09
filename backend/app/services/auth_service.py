"""Authentication: signup, login, refresh, logout."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    hash_password,
    issue_access_token,
    issue_refresh_token,
    needs_rehash,
    verify_password,
)
from app.models import RefreshToken, TeamMember, User, Workspace
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    TokenPair,
    UserResponse,
    WorkspaceMembership,
)


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _memberships(db: AsyncSession, user_id: uuid.UUID) -> list[WorkspaceMembership]:
    stmt = (
        select(TeamMember, Workspace)
        .join(Workspace, Workspace.id == TeamMember.workspace_id)
        .where(TeamMember.user_id == user_id)
        .order_by(Workspace.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        WorkspaceMembership(
            workspace_id=ws.id,
            workspace_name=ws.name,
            workspace_slug=ws.slug,
            role=tm.role,
        )
        for tm, ws in rows
    ]


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[TokenPair, list[WorkspaceMembership]]:
    memberships = await _memberships(db, user.id)
    ws_ids = [m.workspace_id for m in memberships]
    access, exp = issue_access_token(user_id=user.id, workspace_ids=ws_ids)
    refresh, refresh_exp = issue_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_refresh(refresh),
            expires_at=refresh_exp,
        )
    )
    return (
        TokenPair(access_token=access, refresh_token=refresh, expires_at=exp),
        memberships,
    )


async def signup(db: AsyncSession, payload: SignupRequest) -> AuthResponse:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise ConflictError("An account with that email already exists.", code="auth.email_taken")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()
    user.last_login_at = datetime.now(UTC)
    tokens, memberships = await _issue_tokens(db, user)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens, memberships=memberships)


async def login(db: AsyncSession, payload: LoginRequest) -> AuthResponse:
    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.", code="auth.invalid_credentials")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = datetime.now(UTC)
    tokens, memberships = await _issue_tokens(db, user)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens, memberships=memberships)


async def refresh(db: AsyncSession, refresh_token: str) -> TokenPair:
    token_hash = _hash_refresh(refresh_token)
    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if rt is None or rt.revoked_at is not None or rt.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token invalid or expired.", code="auth.refresh_invalid")
    user = await db.get(User, rt.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is inactive.", code="auth.inactive")
    # Rotate
    rt.revoked_at = datetime.now(UTC)
    tokens, _ = await _issue_tokens(db, user)
    new_rt = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh(tokens.refresh_token))
        )
    ).scalar_one_or_none()
    if new_rt:
        rt.rotated_to_id = new_rt.id
    return tokens


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = _hash_refresh(refresh_token)
    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if rt and rt.revoked_at is None:
        rt.revoked_at = datetime.now(UTC)


async def memberships_for(db: AsyncSession, user_id: uuid.UUID) -> list[WorkspaceMembership]:
    return await _memberships(db, user_id)
