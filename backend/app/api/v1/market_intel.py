"""Market intelligence endpoints.

This module exposes two routers:
- ``router``: mounted at ``/market-intel`` (sources, search, records)
- ``links_router``: mounted at the API root (workspace + opportunity scoped)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, OppScope, WorkspaceScope
from app.core.errors import AppError
from app.models import MarketIntelRecord, MarketIntelSource
from app.schemas.market_intel import (
    MarketIntelImportRequest,
    MarketIntelRecordResponse,
    MarketIntelSearchResponse,
    MarketIntelSourceResponse,
    OpportunityMarketIntelLinkCreate,
    OpportunityMarketIntelLinkResponse,
)
from app.services import market_intel_service
from app.services.audit_service import write_audit

router = APIRouter()
links_router = APIRouter()


@router.get("/sources", response_model=list[MarketIntelSourceResponse])
async def list_sources(
    _: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[MarketIntelSourceResponse]:
    rows = (await db.execute(select(MarketIntelSource))).scalars().all()
    return [MarketIntelSourceResponse.model_validate(r) for r in rows]


@router.get("/search", response_model=MarketIntelSearchResponse)
async def search(
    user: CurrentUser,
    source: str = Query(default="sam_gov"),
    q: str | None = Query(default=None),
    agency: str | None = Query(default=None),
    naics: str | None = Query(default=None),
    posted_after: datetime | None = Query(default=None),
    due_before: datetime | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
) -> MarketIntelSearchResponse:
    if source != "sam_gov":
        raise AppError(
            "Only the SAM.gov source is wired up in MVP.",
            status_code=400,
            code="market_intel.unsupported_source",
        )
    payloads = await market_intel_service.search_sam(
        q=q,
        agency=agency,
        naics=naics,
        posted_after=posted_after,
        due_before=due_before,
        limit=limit,
    )
    items = [
        MarketIntelRecordResponse(
            id=uuid.uuid4(),
            source_id=p["source_id"],
            workspace_id=None,
            external_id=p["external_id"],
            source_url=p["source_url"],
            title=p["title"],
            agency=p["agency"],
            sub_agency=p["sub_agency"],
            notice_type=p["notice_type"],
            naics_code=p["naics_code"],
            psc_code=p["psc_code"],
            set_aside=p["set_aside"],
            estimated_value_cents=p["estimated_value_cents"],
            posted_date=p["posted_date"],
            due_date=p["due_date"],
            incumbent=p["incumbent"],
            summary=None,
            fetched_at=None,
        )
        for p in payloads
    ]
    return MarketIntelSearchResponse(items=items, source=source, q=q, total_estimate=len(items))


@router.get("/records/{record_id}", response_model=MarketIntelRecordResponse)
async def get_record(
    record_id: Annotated[uuid.UUID, Path()],
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MarketIntelRecordResponse:
    rec = await db.get(MarketIntelRecord, record_id)
    if rec is None:
        raise AppError("Record not found.", status_code=404, code="market_intel.not_found")
    return MarketIntelRecordResponse.model_validate(rec)


# ── workspace-scoped import + linking (root-mounted) ──


@links_router.post(
    "/workspaces/{workspace_id}/market-intel/import",
    response_model=list[MarketIntelRecordResponse],
)
async def import_records(
    payload: MarketIntelImportRequest,
    scope: WorkspaceScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MarketIntelRecordResponse]:
    ws, _ = scope
    if payload.source_id != "sam_gov":
        raise AppError(
            "Only SAM.gov import is supported in MVP.",
            status_code=400,
            code="market_intel.unsupported_source",
        )
    payloads = await market_intel_service.search_sam(
        q=None, agency=None, naics=None, posted_after=None, due_before=None, limit=100
    )
    filtered = [p for p in payloads if p["external_id"] in set(payload.external_ids)]
    records = await market_intel_service.upsert_records_for_workspace(
        db, workspace_id=ws.id, source_id=payload.source_id, payloads=filtered
    )
    await write_audit(
        db,
        action="market_intel.import",
        workspace_id=ws.id,
        actor_user_id=user.id,
        meta={"source_id": payload.source_id, "count": len(records)},
    )
    return [MarketIntelRecordResponse.model_validate(r) for r in records]


@links_router.post(
    "/opportunities/{opportunity_id}/market-intel-links",
    response_model=OpportunityMarketIntelLinkResponse,
    status_code=201,
)
async def link_record(
    payload: OpportunityMarketIntelLinkCreate,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityMarketIntelLinkResponse:
    ws, _, opportunity_id = scope
    link = await market_intel_service.link_record_to_opportunity(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        market_intel_record_id=payload.market_intel_record_id,
        user_id=user.id,
        notes=payload.notes,
    )
    await write_audit(
        db,
        action="market_intel.linked",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity_market_intel_link",
        target_id=link.id,
        meta={"market_intel_record_id": str(payload.market_intel_record_id)},
    )
    return OpportunityMarketIntelLinkResponse.model_validate(link)


@links_router.get(
    "/opportunities/{opportunity_id}/market-intel-links",
    response_model=list[OpportunityMarketIntelLinkResponse],
)
async def list_links_for_opp(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[OpportunityMarketIntelLinkResponse]:
    _, _, opportunity_id = scope
    rows = await market_intel_service.list_links(db, opportunity_id=opportunity_id)
    return [OpportunityMarketIntelLinkResponse.model_validate(l) for l in rows]
