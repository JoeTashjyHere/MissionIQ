"""Workspace + TeamMember + CompanyProfile + Capability services."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.rbac import require_capability
from app.models import Capability, CompanyProfile, TeamMember, User, Workspace
from app.schemas.workspace import (
    CapabilityCreate,
    CapabilityUpdate,
    CompanyProfileUpdate,
    TeamMemberInvite,
    WorkspaceCreate,
    WorkspaceUpdate,
)


_SLUG_FORBIDDEN = re.compile(r"[^a-z0-9-]+")


def _slugify(name: str) -> str:
    s = _SLUG_FORBIDDEN.sub("-", name.lower()).strip("-")
    return s[:60] or f"ws-{uuid.uuid4().hex[:8]}"


async def list_workspaces(db: AsyncSession, user_id: uuid.UUID) -> list[Workspace]:
    stmt = (
        select(Workspace)
        .join(TeamMember, TeamMember.workspace_id == Workspace.id)
        .where(TeamMember.user_id == user_id)
        .order_by(Workspace.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_workspace(
    db: AsyncSession, user: User, payload: WorkspaceCreate
) -> Workspace:
    slug = payload.slug or _slugify(payload.name)
    suffix = 0
    base = slug
    while True:
        exists = (
            await db.execute(select(Workspace).where(Workspace.slug == slug))
        ).scalar_one_or_none()
        if not exists:
            break
        suffix += 1
        slug = f"{base}-{suffix}"
        if suffix > 100:
            raise ConflictError("Unable to assign a unique workspace slug.", code="workspace.slug_conflict")

    ws = Workspace(
        name=payload.name,
        slug=slug,
        description=payload.description,
        owner_user_id=user.id,
    )
    db.add(ws)
    await db.flush()
    db.add(
        TeamMember(
            workspace_id=ws.id,
            user_id=user.id,
            role="administrator",
            joined_at=datetime.now(UTC),
        )
    )
    db.add(CompanyProfile(workspace_id=ws.id))
    return ws


async def get_workspace_for_user(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Workspace, TeamMember]:
    stmt = (
        select(Workspace, TeamMember)
        .join(TeamMember, TeamMember.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id)
        .where(TeamMember.user_id == user_id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise NotFoundError("Workspace not found.", code="workspace.not_found")
    return row[0], row[1]


async def update_workspace(
    db: AsyncSession, ws: Workspace, member: TeamMember, payload: WorkspaceUpdate
) -> Workspace:
    require_capability(member.role, "workspace.manage")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ws, field, value)
    return ws


async def members(db: AsyncSession, workspace_id: uuid.UUID) -> list[tuple[TeamMember, User]]:
    stmt = (
        select(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.workspace_id == workspace_id)
        .order_by(TeamMember.created_at.asc())
    )
    return [(tm, u) for tm, u in (await db.execute(stmt)).all()]


async def invite_member(
    db: AsyncSession,
    *,
    ws: Workspace,
    actor_membership: TeamMember,
    payload: TeamMemberInvite,
) -> TeamMember:
    require_capability(actor_membership.role, "member.manage")
    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError(
            "User does not exist. Invite-by-email of new users is planned for a later milestone.",
            code="auth.user_not_found",
        )
    existing = (
        await db.execute(
            select(TeamMember).where(
                TeamMember.workspace_id == ws.id, TeamMember.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("User is already a member of this workspace.", code="workspace.member_exists")
    tm = TeamMember(
        workspace_id=ws.id,
        user_id=user.id,
        role=payload.role,
        joined_at=datetime.now(UTC),
    )
    db.add(tm)
    return tm


async def change_member_role(
    db: AsyncSession,
    *,
    ws: Workspace,
    actor_membership: TeamMember,
    member_id: uuid.UUID,
    role: str,
) -> TeamMember:
    require_capability(actor_membership.role, "member.manage")
    tm = await db.get(TeamMember, member_id)
    if tm is None or tm.workspace_id != ws.id:
        raise NotFoundError("Member not found.", code="workspace.member_not_found")
    if tm.user_id == ws.owner_user_id and role != "administrator":
        raise ForbiddenError(
            "The workspace owner is always an administrator.",
            code="workspace.owner_role_locked",
        )
    tm.role = role
    return tm


async def get_company_profile(db: AsyncSession, workspace_id: uuid.UUID) -> CompanyProfile:
    cp = (
        await db.execute(select(CompanyProfile).where(CompanyProfile.workspace_id == workspace_id))
    ).scalar_one_or_none()
    if cp is None:
        cp = CompanyProfile(workspace_id=workspace_id)
        db.add(cp)
        await db.flush()
    return cp


async def update_company_profile(
    db: AsyncSession, workspace_id: uuid.UUID, payload: CompanyProfileUpdate
) -> CompanyProfile:
    cp = await get_company_profile(db, workspace_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cp, k, v)
    return cp


async def list_capabilities(db: AsyncSession, workspace_id: uuid.UUID) -> list[Capability]:
    stmt = (
        select(Capability)
        .where(Capability.workspace_id == workspace_id)
        .order_by(Capability.name.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def add_capability(
    db: AsyncSession, workspace_id: uuid.UUID, payload: CapabilityCreate
) -> Capability:
    cp = await get_company_profile(db, workspace_id)
    cap = Capability(
        workspace_id=workspace_id,
        company_profile_id=cp.id,
        **payload.model_dump(exclude_unset=True),
    )
    db.add(cap)
    await db.flush()
    return cap


async def update_capability(
    db: AsyncSession, capability_id: uuid.UUID, workspace_id: uuid.UUID, payload: CapabilityUpdate
) -> Capability:
    cap = await db.get(Capability, capability_id)
    if cap is None or cap.workspace_id != workspace_id:
        raise NotFoundError("Capability not found.", code="capability.not_found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cap, k, v)
    return cap


async def delete_capability(
    db: AsyncSession, capability_id: uuid.UUID, workspace_id: uuid.UUID
) -> None:
    cap = await db.get(Capability, capability_id)
    if cap is None or cap.workspace_id != workspace_id:
        raise NotFoundError("Capability not found.", code="capability.not_found")
    await db.delete(cap)
