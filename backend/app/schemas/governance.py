"""Collaboration & Governance schemas.

API contracts for comments, the review/approval workflow, human overrides
(decision ledger + feedback capture), assumption validation, and the
pursuit-level decision history timeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

CommentStatus = Literal["open", "resolved"]
ReviewStatus = Literal["draft", "in_review", "approved", "rejected", "archived"]
ReviewAction = Literal["submit", "approve", "reject", "reopen", "archive"]
OverrideType = Literal["decision", "score"]
ValidationStatus = Literal["validated", "rejected"]
# Display status includes the default absence-of-judgment state.
AssumptionStatus = Literal["unvalidated", "validated", "rejected"]


# ── Comments ─────────────────────────────────────────────────────────────────


class CommentCreate(BaseModel):
    target_module_id: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=8000)
    parent_comment_id: uuid.UUID | None = None
    mentions: list[uuid.UUID] = []


class CommentResponse(ORMModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    target_module_id: str
    ai_output_id: uuid.UUID | None
    parent_comment_id: uuid.UUID | None
    body: str
    mentions: list[uuid.UUID]
    status: CommentStatus
    author_user_id: uuid.UUID
    author_name: str
    resolved_by_user_id: uuid.UUID | None
    resolved_by_name: str | None
    resolved_at: datetime | None
    created_at: datetime


# ── Review workflow ──────────────────────────────────────────────────────────


class ReviewActionRequest(BaseModel):
    action: ReviewAction
    notes: str | None = Field(default=None, max_length=8000)


class ReviewEventResponse(ORMModel):
    id: uuid.UUID
    action: Literal["submitted", "approved", "rejected", "reopened", "archived"]
    decision_summary: str | None
    notes: str | None
    actor_user_id: uuid.UUID | None
    actor_name: str | None
    created_at: datetime


class ReviewResponse(ORMModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    module_id: str
    ai_output_id: uuid.UUID | None
    status: ReviewStatus
    generated_at: datetime | None  # the reviewed generation's timestamp
    events: list[ReviewEventResponse]


# ── Human overrides (decision ledger + feedback capture) ─────────────────────


class OverrideCreate(BaseModel):
    module_id: str = Field(min_length=1, max_length=120)
    override_type: OverrideType
    field: str = Field(min_length=1, max_length=200)
    original_value: Any
    override_value: Any
    reason: str = Field(min_length=1, max_length=8000)


class OverrideResponse(ORMModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    ai_output_id: uuid.UUID | None
    module_id: str
    override_type: OverrideType
    field: str
    original_value: Any
    override_value: Any
    reason: str
    created_by_user_id: uuid.UUID | None
    created_by_name: str | None
    created_at: datetime


# ── Assumption validation ────────────────────────────────────────────────────


class AssumptionValidationRecord(ORMModel):
    id: uuid.UUID
    status: ValidationStatus
    notes: str | None
    validator_user_id: uuid.UUID | None
    validator_name: str | None
    created_at: datetime


class AssumptionItem(BaseModel):
    """An assumption extracted from the live AI output, merged with the
    latest human judgment. The original statement is always shown verbatim —
    it lives untouched in ``ai_output.output_json``."""

    key: str
    text: str
    path: str
    status: AssumptionStatus = "unvalidated"
    latest: AssumptionValidationRecord | None = None
    history: list[AssumptionValidationRecord] = []


class AssumptionPanel(BaseModel):
    module_id: str
    ai_output_id: uuid.UUID | None
    assumptions: list[AssumptionItem] = []


class AssumptionValidateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    status: ValidationStatus
    notes: str | None = Field(default=None, max_length=8000)


# ── Decision history timeline ────────────────────────────────────────────────


class DecisionTimelineEntry(BaseModel):
    kind: Literal[
        "generated",
        "review_submitted",
        "review_approved",
        "review_rejected",
        "review_reopened",
        "review_archived",
        "decision_overridden",
        "score_overridden",
        "assumption_validated",
        "assumption_rejected",
        "outcome_recorded",
    ]
    module_id: str | None = None
    label: str
    detail: str | None = None
    original_value: Any = None
    adjusted_value: Any = None
    reason: str | None = None
    actor_name: str | None = None
    occurred_at: datetime


class DecisionHistoryResponse(BaseModel):
    opportunity_id: uuid.UUID
    entries: list[DecisionTimelineEntry] = []
