"""Intelligence outputs: AIOutput + structured derivatives (compliance, evaluation, risk)."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin

AI_STATUSES = ("ok", "insufficient_context", "error")
COMPLIANCE_STATUSES = ("open", "in_progress", "complete", "n_a")
RISK_CATEGORIES = (
    "technical",
    "staffing",
    "schedule",
    "financial",
    "security",
    "compliance",
    "competitive",
    "transition",
    "other",
)
IMPACT_LEVELS = ("low", "medium", "high", "critical")
LIKELIHOOD_LEVELS = ("low", "medium", "high")
RISK_STATUSES = ("open", "mitigated", "accepted", "closed")
IMPORTANCE_LEVELS = (
    "most_important",
    "important",
    "less_important",
    "equal",
    "unspecified",
)


class AIOutput(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ai_output"
    __table_args__ = (
        CheckConstraint(f"status IN {AI_STATUSES!r}", name="ck_ai_output_status"),
        Index(
            "ix_ai_output_ws_opp_module_created",
            "workspace_id",
            "opportunity_id",
            "module_id",
            "created_at",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
    )
    module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    module_version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_chunk_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True))
    )
    evidence_market_record_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True))
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ok")
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )


class ComplianceRequirement(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "compliance_requirement"
    __table_args__ = (
        CheckConstraint(
            f"status IN {COMPLIANCE_STATUSES!r}", name="ck_compliance_status"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id")
    )
    requirement_code: Mapped[str | None] = mapped_column(String(80))
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id")
    )
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_section: Mapped[str | None] = mapped_column(String(200))
    owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    notes: Mapped[str | None] = mapped_column(Text)


class EvaluationCriterion(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_criterion"
    __table_args__ = (
        CheckConstraint(
            f"importance IN {IMPORTANCE_LEVELS!r}", name="ck_eval_importance"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id")
    )
    factor: Mapped[str] = mapped_column(String(200), nullable=False)
    subfactor: Mapped[str | None] = mapped_column(String(200))
    importance: Mapped[str | None] = mapped_column(String(40))
    required_response_elements: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id")
    )
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_section: Mapped[str | None] = mapped_column(String(200))


class Risk(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "risk"
    __table_args__ = (
        CheckConstraint(f"category IN {RISK_CATEGORIES!r}", name="ck_risk_category"),
        CheckConstraint(f"impact IN {IMPACT_LEVELS!r}", name="ck_risk_impact"),
        CheckConstraint(
            f"likelihood IN {LIKELIHOOD_LEVELS!r}", name="ck_risk_likelihood"
        ),
        CheckConstraint(f"status IN {RISK_STATUSES!r}", name="ck_risk_status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id")
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id")
    )
    source_page: Mapped[int | None] = mapped_column(Integer)
    impact: Mapped[str | None] = mapped_column(String(20))
    likelihood: Mapped[str | None] = mapped_column(String(20))
    mitigation: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
