"""Pursuit Automation Orchestrator endpoints."""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, session_scope
from app.core.dependencies import CurrentUser, OppScope, WorkspaceScope
from app.schemas.automation import AutomationRunResponse
from app.services import automation_service
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

router = APIRouter()


async def _execute_in_background(run_id: uuid.UUID) -> None:
    """Background task: fresh session, drive the run to completion."""
    async with session_scope() as db:
        await automation_service.execute_run(db, run_id=run_id)


@router.post(
    "/opportunities/{opportunity_id}/automation/run",
    response_model=AutomationRunResponse,
    status_code=202,
)
async def run_automation(
    background: BackgroundTasks,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutomationRunResponse:
    ws, _, opportunity_id = scope
    run = await automation_service.enqueue_run(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        user_id=user.id,
        trigger="manual",
    )
    background.add_task(_execute_in_background, run.id)
    return AutomationRunResponse.model_validate(run)


@router.get(
    "/opportunities/{opportunity_id}/automation/runs",
    response_model=list[AutomationRunResponse],
)
async def opportunity_runs(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[AutomationRunResponse]:
    ws, _, opportunity_id = scope
    return await automation_service.list_runs_for_opportunity(
        db, workspace_id=ws.id, opportunity_id=opportunity_id
    )


@router.get(
    "/workspaces/{workspace_id}/automation/runs",
    response_model=list[AutomationRunResponse],
)
async def workspace_runs(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AutomationRunResponse]:
    ws, _ = scope
    return await automation_service.list_runs_for_workspace(
        db, workspace_id=ws.id, limit=limit
    )


@router.post(
    "/workspaces/{workspace_id}/automation/runs/{run_id}/retry",
    response_model=AutomationRunResponse,
    status_code=202,
)
async def retry_automation(
    run_id: Annotated[uuid.UUID, Path()],
    background: BackgroundTasks,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutomationRunResponse:
    ws, _ = scope
    run = await automation_service.retry_run(db, workspace_id=ws.id, run_id=run_id)
    await write_audit(
        db,
        action="automation.run.retried",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="automation_run",
        target_id=str(run.id),
    )
    background.add_task(_execute_in_background, run.id)
    return AutomationRunResponse.model_validate(run)
