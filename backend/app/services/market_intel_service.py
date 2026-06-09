"""Market intelligence: SAM.gov search + record upsert + link to opportunity."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.integrations.sam_gov import SamGovClient
from app.models import MarketIntelRecord, Opportunity, OpportunityMarketIntelLink


async def search_sam(
    *,
    q: str | None,
    agency: str | None,
    naics: str | None,
    posted_after: datetime | None,
    due_before: datetime | None,
    limit: int = 25,
) -> list[dict]:
    client = SamGovClient()
    items = await client.search_opportunities(
        q=q,
        agency=agency,
        naics=naics,
        posted_after=posted_after,
        due_before=due_before,
        limit=limit,
    )
    return [SamGovClient.to_record_dict(item) for item in items]


async def upsert_records_for_workspace(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    source_id: str,
    payloads: list[dict],
) -> list[MarketIntelRecord]:
    """Upsert public market records into the global table when workspace_id
    is None, or into the workspace-scoped table when workspace_id is provided.

    For SAM.gov (public), we always insert with workspace_id=NULL so the data
    is shared across workspaces. The workspace_id parameter is used to scope
    AuditLog only.
    """
    if not payloads:
        return []
    # Public sources stay shared; only customer-licensed records use workspace_id.
    classification_workspace_id: uuid.UUID | None = None
    if source_id != "sam_gov":
        classification_workspace_id = workspace_id

    records: list[MarketIntelRecord] = []
    now = datetime.now(UTC)
    for p in payloads:
        p = {**p, "fetched_at": now, "workspace_id": classification_workspace_id}
        if not p["external_id"]:
            continue
        stmt = (
            pg_insert(MarketIntelRecord)
            .values(**p)
            .on_conflict_do_update(
                constraint="uq_mi_record_dedupe",
                set_={
                    "title": p["title"],
                    "agency": p["agency"],
                    "sub_agency": p["sub_agency"],
                    "notice_type": p["notice_type"],
                    "naics_code": p["naics_code"],
                    "psc_code": p["psc_code"],
                    "set_aside": p["set_aside"],
                    "estimated_value_cents": p["estimated_value_cents"],
                    "posted_date": p["posted_date"],
                    "due_date": p["due_date"],
                    "raw_json": p["raw_json"],
                    "fetched_at": now,
                },
            )
            .returning(MarketIntelRecord)
        )
        res = await db.execute(stmt)
        rec = res.scalar_one()
        records.append(rec)
    return records


async def link_record_to_opportunity(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    market_intel_record_id: uuid.UUID,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> OpportunityMarketIntelLink:
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")
    rec = await db.get(MarketIntelRecord, market_intel_record_id)
    if rec is None:
        raise NotFoundError("Market intelligence record not found.", code="market_intel.not_found")
    # If the record is workspace-scoped, ensure it belongs to this workspace.
    if rec.workspace_id is not None and rec.workspace_id != workspace_id:
        raise AppError(
            "Cannot link a market record from another workspace.",
            status_code=403,
            code="market_intel.cross_workspace",
        )
    existing = (
        await db.execute(
            select(OpportunityMarketIntelLink).where(
                OpportunityMarketIntelLink.opportunity_id == opportunity_id,
                OpportunityMarketIntelLink.market_intel_record_id == market_intel_record_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    link = OpportunityMarketIntelLink(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        market_intel_record_id=market_intel_record_id,
        linked_by_user_id=user_id,
        notes=notes,
    )
    db.add(link)
    await db.flush()
    return link


async def list_links(
    db: AsyncSession, *, opportunity_id: uuid.UUID
) -> list[OpportunityMarketIntelLink]:
    stmt = select(OpportunityMarketIntelLink).where(
        OpportunityMarketIntelLink.opportunity_id == opportunity_id
    )
    return list((await db.execute(stmt)).scalars().all())
