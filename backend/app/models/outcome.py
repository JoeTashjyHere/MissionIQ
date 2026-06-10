"""Outcome Intelligence models — the closed-loop learning layer.

``pursuit_outcome`` is the terminal lifecycle artifact for a pursuit: what
actually happened (won / lost / no_bid / cancelled / withdrawn), when, against
whom, and why (debrief factors). Recording one snapshots
``recommendation_outcome`` rows — what MissionIQ recommended at the time vs.
the recorded outcome — and recomputes Knowledge Graph outcome weighting.

Epistemic honesty contract: ``aligned`` records *alignment* between a
recommendation and an outcome. It is a historical correlation, never a causal
claim about why the pursuit was won or lost.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

OUTCOMES = ("won", "lost", "no_bid", "cancelled", "withdrawn")

# Outcomes that count as decided competitions for win/loss statistics.
# no_bid / cancelled / withdrawn are lifecycle ends, not competitive results.
DECIDED_OUTCOMES = ("won", "lost")

RECOMMENDATION_TYPES = (
    "bid_decision",
    "gate_recommendation",
    "win_confidence",
    "executive_recommendation",
)


class PursuitOutcome(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "pursuit_outcome"
    __table_args__ = (
        CheckConstraint(f"outcome IN {OUTCOMES!r}", name="ck_pursuit_outcome"),
        UniqueConstraint("opportunity_id", name="uq_pursuit_outcome_opportunity"),
        Index("ix_pursuit_outcome_ws_outcome", "workspace_id", "outcome"),
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
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    awarded_value_cents: Mapped[int | None] = mapped_column(BigInteger)
    awarded_to_competitor: Mapped[str | None] = mapped_column(String(200))
    # Debrief factors as reported (e.g. "price", "transition approach").
    outcome_factors: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    debrief_notes: Mapped[str | None] = mapped_column(Text)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )

    recommendation_outcomes = relationship(
        "RecommendationOutcome",
        back_populates="pursuit_outcome",
        cascade="all, delete-orphan",
    )


class RecommendationOutcome(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_outcome"
    __table_args__ = (
        CheckConstraint(
            f"recommendation_type IN {RECOMMENDATION_TYPES!r}",
            name="ck_recommendation_type",
        ),
        Index("ix_rec_outcome_ws_type", "workspace_id", "recommendation_type"),
        Index("ix_rec_outcome_opportunity", "opportunity_id"),
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
    pursuit_outcome_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pursuit_outcome.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_output_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_output.id", ondelete="SET NULL")
    )
    module_id: Mapped[str] = mapped_column(String(120), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    predicted_label: Mapped[str | None] = mapped_column(String(80))
    predicted_score: Mapped[float | None] = mapped_column(Float)
    # Alignment between recommendation and recorded outcome. A historical
    # correlation only — NULL when alignment is undefined for the outcome.
    aligned: Mapped[bool | None] = mapped_column(Boolean)

    pursuit_outcome = relationship(
        "PursuitOutcome", back_populates="recommendation_outcomes"
    )
