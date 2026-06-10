"""Outcome Intelligence endpoints — the closed-loop learning layer.

Outcome capture (the terminal lifecycle event for a pursuit) plus the
deterministic workspace analysis: win/loss patterns, trends, recommendation
performance. Everything returned is observed patterns + historical
correlations with supporting evidence — never causal claims.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import OppScope, WorkspaceScope
from app.core.errors import NotFoundError
from app.models import Opportunity, PursuitOutcome
from app.schemas.outcome import (
    OutcomeIntelligenceReport,
    OutcomeRecordRequest,
    PursuitOutcomeResponse,
)
from app.services import outcome_intelligence_service as outcome_service

router = APIRouter()


def _to_response(
    po: PursuitOutcome, opp: Opportunity | None = None
) -> PursuitOutcomeResponse:
    resp = PursuitOutcomeResponse.model_validate(po)
    if opp is not None:
        resp.opportunity_name = opp.name
        resp.agency = opp.agency
    return resp


@router.put(
    "/opportunities/{opportunity_id}/outcome", response_model=PursuitOutcomeResponse
)
async def record_outcome(
    scope: OppScope,
    payload: OutcomeRecordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PursuitOutcomeResponse:
    _, member, opportunity_id = scope
    opp = await db.get(Opportunity, opportunity_id)
    assert opp is not None  # OppScope already resolved it
    po = await outcome_service.record_outcome(
        db, opportunity=opp, payload=payload, user_id=member.user_id
    )
    await db.commit()
    refreshed = await outcome_service.get_outcome(db, opportunity_id=opportunity_id)
    return _to_response(refreshed or po, opp)


@router.get(
    "/opportunities/{opportunity_id}/outcome", response_model=PursuitOutcomeResponse
)
async def get_outcome(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> PursuitOutcomeResponse:
    _, _, opportunity_id = scope
    po = await outcome_service.get_outcome(db, opportunity_id=opportunity_id)
    if po is None:
        raise NotFoundError("No outcome recorded.", code="outcome.not_found")
    opp = await db.get(Opportunity, opportunity_id)
    return _to_response(po, opp)


@router.delete("/opportunities/{opportunity_id}/outcome", status_code=204)
async def delete_outcome(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    _, member, opportunity_id = scope
    opp = await db.get(Opportunity, opportunity_id)
    assert opp is not None
    deleted = await outcome_service.delete_outcome(
        db, opportunity=opp, user_id=member.user_id
    )
    if not deleted:
        raise NotFoundError("No outcome recorded.", code="outcome.not_found")
    await db.commit()


@router.get(
    "/workspaces/{workspace_id}/outcomes",
    response_model=list[PursuitOutcomeResponse],
)
async def list_outcomes(
    scope: WorkspaceScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    outcome: Annotated[str | None, Query()] = None,
) -> list[PursuitOutcomeResponse]:
    ws, _ = scope
    rows = await outcome_service.list_outcomes(
        db, workspace_id=ws.id, outcome=outcome
    )
    return [_to_response(po, opp) for po, opp in rows]


@router.get(
    "/workspaces/{workspace_id}/outcome-intelligence",
    response_model=OutcomeIntelligenceReport,
)
async def outcome_intelligence(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> OutcomeIntelligenceReport:
    ws, _ = scope
    return await outcome_service.build_report(db, workspace_id=ws.id)
