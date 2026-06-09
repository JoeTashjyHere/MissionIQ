"""Company profile + capabilities endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, WorkspaceScope
from app.schemas.workspace import (
    CapabilityCreate,
    CapabilityResponse,
    CapabilityUpdate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)
from app.services import workspace_service

router = APIRouter()


@router.get("/{workspace_id}/company-profile", response_model=CompanyProfileResponse)
async def get_profile(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> CompanyProfileResponse:
    ws, _ = scope
    cp = await workspace_service.get_company_profile(db, ws.id)
    return CompanyProfileResponse.model_validate(cp)


@router.put("/{workspace_id}/company-profile", response_model=CompanyProfileResponse)
async def update_profile(
    payload: CompanyProfileUpdate,
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyProfileResponse:
    ws, _ = scope
    cp = await workspace_service.update_company_profile(db, ws.id, payload)
    return CompanyProfileResponse.model_validate(cp)


@router.get("/{workspace_id}/capabilities", response_model=list[CapabilityResponse])
async def list_caps(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[CapabilityResponse]:
    ws, _ = scope
    rows = await workspace_service.list_capabilities(db, ws.id)
    return [CapabilityResponse.model_validate(c) for c in rows]


@router.post("/{workspace_id}/capabilities", response_model=CapabilityResponse, status_code=201)
async def add_cap(
    payload: CapabilityCreate,
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CapabilityResponse:
    ws, _ = scope
    cap = await workspace_service.add_capability(db, ws.id, payload)
    return CapabilityResponse.model_validate(cap)


@router.patch(
    "/{workspace_id}/capabilities/{capability_id}", response_model=CapabilityResponse
)
async def update_cap(
    capability_id: Annotated[uuid.UUID, Path()],
    payload: CapabilityUpdate,
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CapabilityResponse:
    ws, _ = scope
    cap = await workspace_service.update_capability(db, capability_id, ws.id, payload)
    return CapabilityResponse.model_validate(cap)


@router.delete("/{workspace_id}/capabilities/{capability_id}", status_code=204)
async def delete_cap(
    capability_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    ws, _ = scope
    await workspace_service.delete_capability(db, capability_id, ws.id)
