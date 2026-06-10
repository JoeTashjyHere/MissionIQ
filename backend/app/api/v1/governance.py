"""Collaboration & Governance endpoints.

Comments, the review/approval workflow, human overrides (decision ledger +
feedback capture), assumption validation, and the pursuit decision history
timeline. Original AI intelligence is never modified — every endpoint here
appends human judgment alongside it. RBAC capabilities are enforced in the
service layer; every mutation writes an audit record.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, OppScope
from app.schemas.governance import (
    AssumptionPanel,
    AssumptionValidateRequest,
    CommentCreate,
    CommentResponse,
    DecisionHistoryResponse,
    OverrideCreate,
    OverrideResponse,
    ReviewActionRequest,
    ReviewResponse,
)
from app.services import governance_service

router = APIRouter()


# ── Comments ─────────────────────────────────────────────────────────────────


@router.get(
    "/opportunities/{opportunity_id}/comments", response_model=list[CommentResponse]
)
async def list_comments(
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    module_id: Annotated[str | None, Query()] = None,
) -> list[CommentResponse]:
    _, _, opportunity_id = scope
    return await governance_service.list_comments(
        db, opportunity_id=opportunity_id, module_id=module_id
    )


@router.post(
    "/opportunities/{opportunity_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def create_comment(
    payload: CommentCreate,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    ws, member, opportunity_id = scope
    return await governance_service.create_comment(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        actor=user,
        actor_role=member.role,
        payload=payload,
    )


@router.post(
    "/opportunities/{opportunity_id}/comments/{comment_id}/resolve",
    response_model=CommentResponse,
)
async def resolve_comment(
    comment_id: Annotated[uuid.UUID, Path()],
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    ws, member, opportunity_id = scope
    return await governance_service.set_comment_status(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        comment_id=comment_id,
        actor=user,
        actor_role=member.role,
        resolved=True,
    )


@router.post(
    "/opportunities/{opportunity_id}/comments/{comment_id}/reopen",
    response_model=CommentResponse,
)
async def reopen_comment(
    comment_id: Annotated[uuid.UUID, Path()],
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    ws, member, opportunity_id = scope
    return await governance_service.set_comment_status(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        comment_id=comment_id,
        actor=user,
        actor_role=member.role,
        resolved=False,
    )


# ── Review workflow ──────────────────────────────────────────────────────────


@router.get(
    "/opportunities/{opportunity_id}/modules/{module_id}/review",
    response_model=ReviewResponse,
)
async def get_review(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewResponse:
    ws, _, opportunity_id = scope
    return await governance_service.get_or_create_review(
        db, workspace_id=ws.id, opportunity_id=opportunity_id, module_id=module_id
    )


@router.get(
    "/opportunities/{opportunity_id}/modules/{module_id}/review/history",
    response_model=list[ReviewResponse],
)
async def get_review_history(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ReviewResponse]:
    _, _, opportunity_id = scope
    return await governance_service.review_history(
        db, opportunity_id=opportunity_id, module_id=module_id
    )


@router.post(
    "/opportunities/{opportunity_id}/modules/{module_id}/review",
    response_model=ReviewResponse,
)
async def act_on_review(
    module_id: Annotated[str, Path()],
    payload: ReviewActionRequest,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewResponse:
    ws, member, opportunity_id = scope
    return await governance_service.act_on_review(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        module_id=module_id,
        actor=user,
        actor_role=member.role,
        action=payload.action,
        notes=payload.notes,
    )


# ── Assumption validation ────────────────────────────────────────────────────


@router.get(
    "/opportunities/{opportunity_id}/modules/{module_id}/assumptions",
    response_model=AssumptionPanel,
)
async def get_assumptions(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssumptionPanel:
    ws, _, opportunity_id = scope
    return await governance_service.assumption_panel(
        db, workspace_id=ws.id, opportunity_id=opportunity_id, module_id=module_id
    )


@router.post(
    "/opportunities/{opportunity_id}/modules/{module_id}/assumptions/validate",
    response_model=AssumptionPanel,
)
async def validate_assumption(
    module_id: Annotated[str, Path()],
    payload: AssumptionValidateRequest,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssumptionPanel:
    ws, member, opportunity_id = scope
    return await governance_service.validate_assumption(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        module_id=module_id,
        actor=user,
        actor_role=member.role,
        payload=payload,
    )


# ── Human overrides ──────────────────────────────────────────────────────────


@router.get(
    "/opportunities/{opportunity_id}/overrides", response_model=list[OverrideResponse]
)
async def list_overrides(
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    module_id: Annotated[str | None, Query()] = None,
) -> list[OverrideResponse]:
    _, _, opportunity_id = scope
    return await governance_service.list_overrides(
        db, opportunity_id=opportunity_id, module_id=module_id
    )


@router.post(
    "/opportunities/{opportunity_id}/overrides",
    response_model=OverrideResponse,
    status_code=201,
)
async def create_override(
    payload: OverrideCreate,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverrideResponse:
    ws, member, opportunity_id = scope
    return await governance_service.create_override(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        actor=user,
        actor_role=member.role,
        payload=payload,
    )


# ── Decision history ─────────────────────────────────────────────────────────


@router.get(
    "/opportunities/{opportunity_id}/decision-history",
    response_model=DecisionHistoryResponse,
)
async def get_decision_history(
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DecisionHistoryResponse:
    ws, _, opportunity_id = scope
    return await governance_service.decision_history(
        db, workspace_id=ws.id, opportunity_id=opportunity_id
    )
