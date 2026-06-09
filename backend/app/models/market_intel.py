"""Market intelligence catalog + records + opportunity links."""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

CLASSIFICATIONS = ("public", "customer_licensed", "customer_uploaded")
AUTH_MODES = ("none", "api_key", "oauth", "customer_credentials")


class MarketIntelSource(Base):
    """Static catalog of integrated sources."""

    __tablename__ = "market_intel_source"
    __table_args__ = (
        CheckConstraint(
            f"classification IN {CLASSIFICATIONS!r}", name="ck_mi_source_classification"
        ),
        CheckConstraint(f"auth_mode IN {AUTH_MODES!r}", name="ck_mi_source_auth_mode"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MarketIntelRecord(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "market_intel_record"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_id", "workspace_id", name="uq_mi_record_dedupe"
        ),
        Index("ix_mi_record_source_ws_due", "source_id", "workspace_id", "due_date"),
        Index("ix_mi_record_agency_due", "agency", "due_date"),
    )

    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("market_intel_source.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=True,
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    agency: Mapped[str | None] = mapped_column(String(200))
    sub_agency: Mapped[str | None] = mapped_column(String(200))
    notice_type: Mapped[str | None] = mapped_column(String(80))
    naics_code: Mapped[str | None] = mapped_column(String(16))
    psc_code: Mapped[str | None] = mapped_column(String(16))
    set_aside: Mapped[str | None] = mapped_column(String(80))
    estimated_value_cents: Mapped[int | None] = mapped_column(BigInteger)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    incumbent: Mapped[str | None] = mapped_column(String(200))
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpportunityMarketIntelLink(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_market_intel_link"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "market_intel_record_id", name="uq_opp_mi_link"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_intel_record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_intel_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    relevance: Mapped[float | None] = mapped_column(Numeric(4, 3))
    notes: Mapped[str | None] = mapped_column(Text)

    record = relationship("MarketIntelRecord")
