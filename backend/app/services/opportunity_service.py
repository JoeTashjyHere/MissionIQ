"""Opportunity CRUD + overview roll-up."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import AIOutput, ComplianceRequirement, Document, Opportunity, Risk, User
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityOverview,
    OpportunityResponse,
    OpportunityUpdate,
)


async def list_opportunities(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    stage: str | None = None,
    agency: str | None = None,
    due_before: datetime | None = None,
    q: str | None = None,
    limit: int = 50,
) -> list[Opportunity]:
    stmt = select(Opportunity).where(Opportunity.workspace_id == workspace_id)
    if stage:
        stmt = stmt.where(Opportunity.capture_stage == stage)
    if agency:
        stmt = stmt.where(Opportunity.agency == agency)
    if due_before:
        stmt = stmt.where(Opportunity.due_date <= due_before)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Opportunity.name.ilike(like))
    stmt = stmt.order_by(Opportunity.created_at.desc()).limit(min(max(limit, 1), 200))
    return list((await db.execute(stmt)).scalars().all())


async def create_opportunity(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user: User,
    payload: OpportunityCreate,
) -> Opportunity:
    opp = Opportunity(
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        **payload.model_dump(exclude_unset=True),
    )
    db.add(opp)
    await db.flush()
    return opp


async def get_opportunity(
    db: AsyncSession, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> Opportunity:
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")
    return opp


async def update_opportunity(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    payload: OpportunityUpdate,
) -> Opportunity:
    opp = await get_opportunity(db, workspace_id, opportunity_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(opp, k, v)
    return opp


async def delete_opportunity(
    db: AsyncSession, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> None:
    opp = await get_opportunity(db, workspace_id, opportunity_id)
    await db.delete(opp)


async def overview(
    db: AsyncSession, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> OpportunityOverview:
    opp = await get_opportunity(db, workspace_id, opportunity_id)
    doc_total = (
        await db.execute(
            select(func.count(Document.id)).where(Document.opportunity_id == opp.id)
        )
    ).scalar_one()
    doc_ready = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.opportunity_id == opp.id, Document.status == "ready"
            )
        )
    ).scalar_one()
    ai_total = (
        await db.execute(
            select(func.count(AIOutput.id)).where(AIOutput.opportunity_id == opp.id)
        )
    ).scalar_one()
    last_ai = (
        await db.execute(
            select(func.max(AIOutput.created_at)).where(AIOutput.opportunity_id == opp.id)
        )
    ).scalar_one()
    risk_total = (
        await db.execute(select(func.count(Risk.id)).where(Risk.opportunity_id == opp.id))
    ).scalar_one()
    risk_open = (
        await db.execute(
            select(func.count(Risk.id)).where(
                Risk.opportunity_id == opp.id, Risk.status == "open"
            )
        )
    ).scalar_one()
    comp_total = (
        await db.execute(
            select(func.count(ComplianceRequirement.id)).where(
                ComplianceRequirement.opportunity_id == opp.id
            )
        )
    ).scalar_one()
    comp_complete = (
        await db.execute(
            select(func.count(ComplianceRequirement.id)).where(
                ComplianceRequirement.opportunity_id == opp.id,
                ComplianceRequirement.status == "complete",
            )
        )
    ).scalar_one()
    return OpportunityOverview(
        opportunity=OpportunityResponse.model_validate(opp),
        document_count=doc_total,
        ready_document_count=doc_ready,
        ai_output_count=ai_total,
        risk_count=risk_total,
        open_risk_count=risk_open,
        compliance_total=comp_total,
        compliance_complete=comp_complete,
        last_ai_generation_at=last_ai,
    )
