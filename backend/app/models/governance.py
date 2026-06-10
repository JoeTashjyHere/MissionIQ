"""Collaboration & Governance models.

Governance philosophy, enforced structurally: ``ai_output`` rows are immutable
generation records that nothing in this layer writes to. Every human judgment
— comment, review transition, approval, override, assumption validation — is a
new row in its own table, linked to the ``ai_output_id`` it judges. Preserving
the original AI intelligence is therefore a schema guarantee.

Append-only ledgers (no update/delete paths exist in the service layer):
``review_event``, ``human_override``, ``assumption_validation``,
``governance_signal``. Comments are body-immutable; only their open/resolved
status toggles. Reviews are status-only state machines whose full history
lives in ``review_event``.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

# Modules whose outputs support comments, assumption validation, and feedback.
GOVERNED_MODULES = (
    "capture.customer_dna",
    "capture.company_dna",
    "capture.capability_match",
    "capture.win_strategy",
    "capture.executive_brief",
    "capture.gate_review",
    "capture.bid_decision",
    "capture.outcome_intelligence",
)

# Deliverables that move through the review/approval workflow.
REVIEWABLE_MODULES = (
    "capture.win_strategy",
    "capture.executive_brief",
    "capture.gate_review",
    "capture.bid_decision",
)

COMMENT_STATUSES = ("open", "resolved")

REVIEW_STATUSES = ("draft", "in_review", "approved", "rejected", "archived")

REVIEW_ACTIONS = ("submitted", "approved", "rejected", "reopened", "archived")

OVERRIDE_TYPES = ("decision", "score")

# A validation row asserts a judgment; "unvalidated" is the absence of rows.
VALIDATION_STATUSES = ("validated", "rejected")

SIGNAL_TYPES = (
    "assumption_validated",
    "assumption_rejected",
    "decision_overridden",
    "score_overridden",
    "review_approved",
    "review_rejected",
    "comment_resolved",
)


class Comment(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "comment"
    __table_args__ = (
        CheckConstraint(f"status IN {COMMENT_STATUSES!r}", name="ck_comment_status"),
        Index("ix_comment_opp_module", "opportunity_id", "target_module_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    # The generation the comment was written against (kept on regenerate).
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id", ondelete="SET NULL")
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comment.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeliverableReview(UUIDPkMixin, TimestampMixin, Base):
    """The active review cycle for one deliverable generation.

    Status-only updates via the state machine in ``governance_service``; the
    immutable record of every transition is ``review_event``. Regenerating a
    deliverable archives the cycle bound to the stale output and a fresh
    draft cycle begins, so an approval can never refer to changed content.
    """

    __tablename__ = "deliverable_review"
    __table_args__ = (
        CheckConstraint(f"status IN {REVIEW_STATUSES!r}", name="ck_review_status"),
        Index("ix_review_opp_module", "opportunity_id", "module_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    events = relationship(
        "ReviewEvent",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewEvent.created_at",
    )


class ReviewEvent(UUIDPkMixin, Base):
    """Append-only transition ledger — the immutable approval record."""

    __tablename__ = "review_event"
    __table_args__ = (
        CheckConstraint(f"action IN {REVIEW_ACTIONS!r}", name="ck_review_event_action"),
        Index("ix_review_event_review", "review_id", "created_at"),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deliverable_review.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # Deliverable recommendation snapshotted at decision time
    # (e.g. "Pursue Aggressively"), so the approval record is self-contained.
    decision_summary: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    review = relationship("DeliverableReview", back_populates="events")


class HumanOverride(UUIDPkMixin, Base):
    """Append-only human adjustment of an AI recommendation.

    Backs both the Decision Ledger (``override_type='decision'``) and Human
    Feedback capture (``override_type='score'``). The original AI value is
    snapshotted alongside the override — never overwritten — and superseding
    an override means writing a new row.
    """

    __tablename__ = "human_override"
    __table_args__ = (
        CheckConstraint(f"override_type IN {OVERRIDE_TYPES!r}", name="ck_override_type"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_override_reason_nonempty"),
        Index("ix_override_opp_module", "opportunity_id", "module_id"),
        Index("ix_override_ws_created", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id", ondelete="SET NULL")
    )
    module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    override_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Dotted path into output_json, e.g. "win_confidence_assessment.score".
    field: Mapped[str] = mapped_column(String(200), nullable=False)
    original_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    override_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssumptionValidation(UUIDPkMixin, Base):
    """Append-only human judgment on an AI-generated assumption.

    The assumption itself lives untouched in ``ai_output.output_json``; the
    snapshot here (``assumption_text``) keeps the record self-contained. The
    latest row per ``assumption_key`` is the current status; prior rows are
    history. No row means "unvalidated".
    """

    __tablename__ = "assumption_validation"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALIDATION_STATUSES!r}", name="ck_validation_status"
        ),
        Index("ix_validation_output_key", "ai_output_id", "assumption_key"),
        Index("ix_validation_opp_module", "opportunity_id", "module_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_output_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_output.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    # Stable sha256 of (path, statement) — see governance_service.assumption_key.
    assumption_key: Mapped[str] = mapped_column(String(64), nullable=False)
    assumption_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    validator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GovernanceSignal(UUIDPkMixin, Base):
    """Append-only institutional-memory signal from human judgment.

    Collected and stored only — per the governance milestone, recommendation
    logic, prompts, and Knowledge Graph weighting do NOT consume these yet.
    """

    __tablename__ = "governance_signal"
    __table_args__ = (
        CheckConstraint(f"signal_type IN {SIGNAL_TYPES!r}", name="ck_signal_type"),
        Index("ix_signal_ws_type", "workspace_id", "signal_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="CASCADE")
    )
    module_id: Mapped[str | None] = mapped_column(String(120))
    signal_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # What was judged: assumption text, overridden field, deliverable label.
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
