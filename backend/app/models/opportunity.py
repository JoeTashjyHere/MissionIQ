"""Opportunity model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

CAPTURE_STAGES = (
    "identification",
    "qualification",
    "pursue",
    "capture",
    "proposal",
    "submitted",
    "awarded",
    "lost",
    "no-bid",
)


class Opportunity(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "opportunity"
    __table_args__ = (
        CheckConstraint(
            f"capture_stage IN {CAPTURE_STAGES!r}",
            name="ck_opportunity_stage",
        ),
        Index("ix_opp_ws_stage", "workspace_id", "capture_stage"),
        Index("ix_opp_ws_due", "workspace_id", "due_date"),
        Index("ix_opp_ws_agency", "workspace_id", "agency"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    agency: Mapped[str | None] = mapped_column(String(200))
    sub_agency: Mapped[str | None] = mapped_column(String(200))
    contract_vehicle: Mapped[str | None] = mapped_column(String(200))
    solicitation_number: Mapped[str | None] = mapped_column(String(100))
    naics_code: Mapped[str | None] = mapped_column(String(16))
    psc_code: Mapped[str | None] = mapped_column(String(16))
    set_aside: Mapped[str | None] = mapped_column(String(80))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_value_cents: Mapped[int | None] = mapped_column(BigInteger)
    capture_stage: Mapped[str] = mapped_column(
        String(40), nullable=False, default="identification"
    )
    incumbent: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )

    workspace = relationship("Workspace", back_populates="opportunities")
    documents = relationship(
        "Document", back_populates="opportunity", cascade="all, delete-orphan"
    )
