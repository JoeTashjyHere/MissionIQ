"""Proposal Intelligence Repository API."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, OppScope, WorkspaceScope
from app.core.errors import NotFoundError
from app.schemas.proposal_repository import (
    AssetSearchParams,
    ProposalAssetDetail,
    ProposalAssetResponse,
    ProposalIntelligenceReport,
    ProposalQueryRequest,
)
from app.services import proposal_extraction_service as extraction_service
from app.services import proposal_repository_service as repo_service

router = APIRouter()


@router.get(
    "/workspaces/{workspace_id}/proposal-assets",
    response_model=list[ProposalAssetResponse],
)
async def list_assets(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str | None, Query()] = None,
    asset_type: Annotated[str | None, Query()] = None,
    agency: Annotated[str | None, Query()] = None,
    outcome: Annotated[str | None, Query()] = None,
    min_win_rate: Annotated[float | None, Query()] = None,
    author: Annotated[str | None, Query()] = None,
    search_mode: Annotated[str, Query()] = "hybrid",
    library: Annotated[str, Query()] = "all",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProposalAssetResponse]:
    ws, _ = scope
    params = AssetSearchParams(
        q=q,
        asset_type=asset_type,
        agency=agency,
        outcome=outcome,
        min_win_rate=min_win_rate,
        author=author,
        search_mode=search_mode,  # type: ignore[arg-type]
        limit=limit,
        offset=offset,
    )
    return await repo_service.search_assets(
        db, workspace_id=ws.id, params=params, library=library
    )


@router.get(
    "/workspaces/{workspace_id}/proposal-assets/{asset_id}",
    response_model=ProposalAssetDetail,
)
async def get_asset(
    asset_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProposalAssetDetail:
    ws, _ = scope
    detail = await repo_service.get_asset_detail(
        db, workspace_id=ws.id, asset_id=asset_id
    )
    if detail is None:
        raise NotFoundError("Asset not found.", code="proposal.asset_not_found")
    return detail


@router.get(
    "/workspaces/{workspace_id}/proposal-assets/{asset_id}/similar",
    response_model=list[ProposalAssetResponse],
)
async def similar_assets(
    asset_id: Annotated[uuid.UUID, Path()],
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    top_k: Annotated[int, Query(ge=1, le=25)] = 8,
) -> list[ProposalAssetResponse]:
    ws, _ = scope
    return await repo_service.similar_assets(
        db, workspace_id=ws.id, asset_id=asset_id, top_k=top_k
    )


@router.post(
    "/opportunities/{opportunity_id}/documents/{document_id}/extract-assets",
    response_model=list[ProposalAssetResponse],
    status_code=201,
)
async def extract_assets(
    document_id: Annotated[uuid.UUID, Path()],
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProposalAssetResponse]:
    ws, _, opportunity_id = scope
    created = await extraction_service.extract_proposal_assets(
        db, document_id=document_id, actor_user_id=user.id
    )
    return await repo_service.enrich_assets(db, created)


@router.get(
    "/workspaces/{workspace_id}/proposal-intelligence",
    response_model=ProposalIntelligenceReport,
)
async def proposal_intelligence_report(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProposalIntelligenceReport:
    ws, _ = scope
    return await repo_service.build_report(db, workspace_id=ws.id)


@router.post(
    "/workspaces/{workspace_id}/proposal-intelligence/query",
    response_model=ProposalIntelligenceReport,
)
async def proposal_intelligence_query(
    payload: ProposalQueryRequest,
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProposalIntelligenceReport:
    """Deterministic query via search filters (LLM synthesis is module-scoped)."""
    ws, _ = scope
    params = AssetSearchParams(
        q=payload.query,
        agency=payload.agency,
        asset_type=payload.asset_types[0] if len(payload.asset_types) == 1 else None,
        limit=30,
    )
    await repo_service.search_assets(db, workspace_id=ws.id, params=params)
    return await repo_service.build_report(db, workspace_id=ws.id)
