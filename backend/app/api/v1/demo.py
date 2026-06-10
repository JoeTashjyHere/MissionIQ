"""Demo workspace API — load the Apex Federal showcase environment."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser
from app.core.errors import ForbiddenError
from app.models import TeamMember, Workspace
from app.services.demo_workspace_service import load_demo_workspace
from seeds.apex.constants import WORKSPACE_SLUG

router = APIRouter()


class DemoLoadResponse(BaseModel):
    status: str
    workspace_slug: str
    workspace_id: str | None = None
    login_email: str
    login_password: str
    message: str


@router.post("/demo/load", response_model=DemoLoadResponse)
async def load_demo(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DemoLoadResponse:
    """Load (or refresh) the Apex Federal showcase workspace.

    Idempotent — safe to run multiple times. Requires administrator role.
    """
    admin = (
        await db.execute(
            select(TeamMember)
            .where(TeamMember.user_id == user.id)
            .where(TeamMember.role == "administrator")
            .limit(1)
        )
    ).scalar_one_or_none()
    if admin is None:
        raise ForbiddenError(
            "Only workspace administrators can load the demo environment.",
            code="demo.admin_required",
        )
    info = await load_demo_workspace(if_empty=False)
    ws = (
        await db.execute(select(Workspace).where(Workspace.slug == WORKSPACE_SLUG))
    ).scalar_one_or_none()
    if ws is not None:
        member = (
            await db.execute(
                select(TeamMember)
                .where(TeamMember.workspace_id == ws.id)
                .where(TeamMember.user_id == user.id)
            )
        ).scalar_one_or_none()
        if member is None:
            from datetime import UTC, datetime

            db.add(
                TeamMember(
                    workspace_id=ws.id,
                    user_id=user.id,
                    role="administrator",
                    joined_at=datetime.now(UTC),
                )
            )
            await db.flush()
        info["workspace_id"] = str(ws.id)
    return DemoLoadResponse(
        status="ok",
        workspace_slug=info["workspace"],
        workspace_id=info.get("workspace_id") or None,
        login_email=info["email"],
        login_password=info["password"],
        message=(
            "Apex Federal Solutions showcase loaded. Switch to the apex-federal "
            "workspace to explore the demo portfolio."
        ),
    )
