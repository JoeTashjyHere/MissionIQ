"""Connector framework endpoints: provider catalog, connector lifecycle,
sync jobs, and connector health observability."""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, session_scope
from app.core.dependencies import CurrentUser, WorkspaceScope
from app.schemas.connector import (
    ConnectorCreate,
    ConnectorHealthSummary,
    ConnectorProviderSpec,
    ConnectorResponse,
    ConnectorTestResult,
    ConnectorUpdate,
    SyncJobResponse,
)
from app.services import connector_service
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sync_in_background(job_id: uuid.UUID) -> None:
    """Background task: fresh session, run the sync job to completion."""
    async with session_scope() as db:
        await connector_service.run_sync_job(db, job_id=job_id)


@router.get("/connectors/providers", response_model=list[ConnectorProviderSpec])
async def list_providers(user: CurrentUser) -> list[ConnectorProviderSpec]:
    return connector_service.list_providers()


# NOTE: declared before /connectors/{connector_id} so "health" never matches
# the path parameter.
@router.get(
    "/workspaces/{workspace_id}/connectors/health",
    response_model=ConnectorHealthSummary,
)
async def connector_health(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> ConnectorHealthSummary:
    ws, _ = scope
    return await connector_service.health_summary(db, workspace_id=ws.id)


@router.get(
    "/workspaces/{workspace_id}/connectors", response_model=list[ConnectorResponse]
)
async def list_connectors(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[ConnectorResponse]:
    ws, _ = scope
    return await connector_service.list_connectors(db, ws.id)


@router.post(
    "/workspaces/{workspace_id}/connectors",
    response_model=ConnectorResponse,
    status_code=201,
)
async def create_connector(
    payload: ConnectorCreate,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectorResponse:
    ws, _ = scope
    connector = await connector_service.create_connector(
        db, workspace_id=ws.id, user_id=user.id, payload=payload
    )
    await write_audit(
        db,
        action="connector.created",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="connector",
        target_id=str(connector.id),
        meta={"provider_id": connector.provider_id, "name": connector.name},
    )
    return await connector_service.to_response(db, connector)


@router.get(
    "/workspaces/{workspace_id}/connectors/{connector_id}",
    response_model=ConnectorResponse,
)
async def get_connector(
    connector_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectorResponse:
    ws, _ = scope
    connector = await connector_service.get_connector(db, ws.id, connector_id)
    return await connector_service.to_response(db, connector)


@router.patch(
    "/workspaces/{workspace_id}/connectors/{connector_id}",
    response_model=ConnectorResponse,
)
async def update_connector(
    connector_id: Annotated[uuid.UUID, Path()],
    payload: ConnectorUpdate,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectorResponse:
    ws, _ = scope
    connector = await connector_service.update_connector(
        db, workspace_id=ws.id, connector_id=connector_id, payload=payload
    )
    await write_audit(
        db,
        action="connector.updated",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="connector",
        target_id=str(connector.id),
        meta={"credential_rotated": payload.credential is not None},
    )
    return await connector_service.to_response(db, connector)


@router.delete(
    "/workspaces/{workspace_id}/connectors/{connector_id}", status_code=204
)
async def delete_connector(
    connector_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    ws, _ = scope
    await connector_service.delete_connector(
        db, workspace_id=ws.id, connector_id=connector_id
    )
    await write_audit(
        db,
        action="connector.deleted",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="connector",
        target_id=str(connector_id),
    )


@router.post(
    "/workspaces/{workspace_id}/connectors/{connector_id}/test",
    response_model=ConnectorTestResult,
)
async def test_connector(
    connector_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectorTestResult:
    ws, _ = scope
    result = await connector_service.test_connection(
        db, workspace_id=ws.id, connector_id=connector_id
    )
    await write_audit(
        db,
        action="connector.tested",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="connector",
        target_id=str(connector_id),
        meta={"ok": result.ok},
    )
    return result


@router.post(
    "/workspaces/{workspace_id}/connectors/{connector_id}/sync",
    response_model=SyncJobResponse,
    status_code=202,
)
async def trigger_sync(
    connector_id: Annotated[uuid.UUID, Path()],
    background: BackgroundTasks,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncJobResponse:
    ws, _ = scope
    job = await connector_service.enqueue_sync_job(
        db,
        workspace_id=ws.id,
        connector_id=connector_id,
        user_id=user.id,
        trigger="manual",
    )
    await write_audit(
        db,
        action="connector.sync.requested",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="connector",
        target_id=str(connector_id),
        meta={"job_id": str(job.id)},
    )
    background.add_task(_sync_in_background, job.id)
    connector = await connector_service.get_connector(db, ws.id, connector_id)
    return SyncJobResponse.model_validate(
        job, update={"connector_name": connector.name, "provider_id": connector.provider_id}
    )


@router.get(
    "/workspaces/{workspace_id}/connectors/{connector_id}/jobs",
    response_model=list[SyncJobResponse],
)
async def connector_jobs(
    connector_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SyncJobResponse]:
    ws, _ = scope
    return await connector_service.list_jobs(
        db, workspace_id=ws.id, connector_id=connector_id, limit=limit
    )


@router.get(
    "/workspaces/{workspace_id}/sync-jobs", response_model=list[SyncJobResponse]
)
async def workspace_sync_jobs(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SyncJobResponse]:
    ws, _ = scope
    return await connector_service.list_jobs(db, workspace_id=ws.id, limit=limit)
