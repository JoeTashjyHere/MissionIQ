"""Opportunity endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, OppScope, WorkspaceScope
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityOverview,
    OpportunityResponse,
    OpportunityUpdate,
)
from app.services import opportunity_service
from app.services.audit_service import write_audit

router = APIRouter()


@router.get(
    "/workspaces/{workspace_id}/opportunities",
    response_model=list[OpportunityResponse],
)
async def list_opps(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    stage: str | None = Query(default=None),
    agency: str | None = Query(default=None),
    due_before: datetime | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OpportunityResponse]:
    ws, _ = scope
    items = await opportunity_service.list_opportunities(
        db, ws.id, stage=stage, agency=agency, due_before=due_before, q=q, limit=limit
    )
    return [OpportunityResponse.model_validate(o) for o in items]


@router.post(
    "/workspaces/{workspace_id}/opportunities",
    response_model=OpportunityResponse,
    status_code=201,
)
async def create_opp(
    payload: OpportunityCreate,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityResponse:
    ws, _ = scope
    opp = await opportunity_service.create_opportunity(db, ws.id, user, payload)
    await write_audit(
        db,
        action="opportunity.created",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity",
        target_id=opp.id,
        meta={"name": opp.name, "agency": opp.agency},
    )
    return OpportunityResponse.model_validate(opp)


@router.get(
    "/workspaces/{workspace_id}/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
)
async def get_opp(
    opportunity_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityResponse:
    ws, _ = scope
    opp = await opportunity_service.get_opportunity(db, ws.id, opportunity_id)
    return OpportunityResponse.model_validate(opp)


@router.patch(
    "/workspaces/{workspace_id}/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
)
async def update_opp(
    opportunity_id: Annotated[uuid.UUID, Path()],
    payload: OpportunityUpdate,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityResponse:
    ws, _ = scope
    opp = await opportunity_service.update_opportunity(db, ws.id, opportunity_id, payload)
    await write_audit(
        db,
        action="opportunity.updated",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity",
        target_id=opp.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    return OpportunityResponse.model_validate(opp)


@router.delete(
    "/workspaces/{workspace_id}/opportunities/{opportunity_id}", status_code=204
)
async def delete_opp(
    opportunity_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    ws, _ = scope
    await opportunity_service.delete_opportunity(db, ws.id, opportunity_id)
    await write_audit(
        db,
        action="opportunity.deleted",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity",
        target_id=opportunity_id,
    )


@router.get(
    "/opportunities/{opportunity_id}/overview", response_model=OpportunityOverview
)
async def overview(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> OpportunityOverview:
    ws, _, opportunity_id = scope
    return await opportunity_service.overview(db, ws.id, opportunity_id)
