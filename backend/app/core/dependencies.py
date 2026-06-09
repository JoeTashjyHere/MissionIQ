"""FastAPI dependencies: current user, workspace scope, request context."""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import TeamMember, User, Workspace
from sqlalchemy import select


async def current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.", code="auth.missing_token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as e:  # noqa: F841
        raise UnauthorizedError("Access token expired.", code="auth.token_expired") from None
    except jwt.InvalidTokenError as e:  # noqa: F841
        raise UnauthorizedError("Invalid access token.", code="auth.token_invalid") from None
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject.", code="auth.token_invalid")
    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is inactive.", code="auth.inactive")
    request.state.user_id = str(user.id)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def workspace_scope(
    workspace_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, TeamMember]:
    stmt = (
        select(Workspace, TeamMember)
        .join(TeamMember, TeamMember.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id)
        .where(TeamMember.user_id == user.id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise NotFoundError("Workspace not found.", code="workspace.not_found")
    return row[0], row[1]


WorkspaceScope = Annotated[tuple[Workspace, TeamMember], Depends(workspace_scope)]


async def workspace_for_opportunity(
    opportunity_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, TeamMember, uuid.UUID]:
    """Resolve workspace from an opportunity_id path param and verify membership."""
    from app.models import Opportunity

    opp = await db.get(Opportunity, opportunity_id)
    if opp is None:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")
    stmt = (
        select(Workspace, TeamMember)
        .join(TeamMember, TeamMember.workspace_id == Workspace.id)
        .where(Workspace.id == opp.workspace_id)
        .where(TeamMember.user_id == user.id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise ForbiddenError("Access denied to this opportunity.", code="opportunity.forbidden")
    return row[0], row[1], opp.id


OppScope = Annotated[
    tuple[Workspace, TeamMember, uuid.UUID], Depends(workspace_for_opportunity)
]
