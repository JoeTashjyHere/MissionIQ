"""Workspace + team endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, WorkspaceScope
from app.schemas.workspace import (
    TeamMemberInvite,
    TeamMemberResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services import workspace_service
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[WorkspaceResponse]:
    items = await workspace_service.list_workspaces(db, user.id)
    return [WorkspaceResponse.model_validate(w) for w in items]


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    ws = await workspace_service.create_workspace(db, user, payload)
    await write_audit(
        db,
        action="workspace.created",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="workspace",
        target_id=ws.id,
        meta={"name": ws.name, "slug": ws.slug},
    )
    return WorkspaceResponse.model_validate(ws)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(scope: WorkspaceScope) -> WorkspaceResponse:
    ws, _member = scope
    return WorkspaceResponse.model_validate(ws)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    payload: WorkspaceUpdate,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    ws, member = scope
    updated = await workspace_service.update_workspace(db, ws, member, payload)
    await write_audit(
        db,
        action="workspace.updated",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="workspace",
        target_id=ws.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    return WorkspaceResponse.model_validate(updated)


@router.get("/{workspace_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[TeamMemberResponse]:
    ws, _ = scope
    rows = await workspace_service.members(db, ws.id)
    return [
        TeamMemberResponse(
            id=tm.id,
            user_id=tm.user_id,
            workspace_id=tm.workspace_id,
            role=tm.role,
            user_email=u.email,
            user_full_name=u.full_name,
            joined_at=tm.joined_at,
            created_at=tm.created_at,
        )
        for tm, u in rows
    ]


@router.post("/{workspace_id}/members", response_model=TeamMemberResponse, status_code=201)
async def invite_member(
    payload: TeamMemberInvite,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberResponse:
    ws, actor_member = scope
    tm = await workspace_service.invite_member(
        db, ws=ws, actor_membership=actor_member, payload=payload
    )
    await write_audit(
        db,
        action="workspace.member_added",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="team_member",
        target_id=tm.id,
        meta={"role": tm.role, "email": payload.email},
    )
    # Reload with user info
    from sqlalchemy import select
    from app.models import User

    u = await db.get(User, tm.user_id)
    return TeamMemberResponse(
        id=tm.id,
        user_id=tm.user_id,
        workspace_id=tm.workspace_id,
        role=tm.role,
        user_email=u.email if u else "",
        user_full_name=u.full_name if u else "",
        joined_at=tm.joined_at,
        created_at=tm.created_at,
    )
