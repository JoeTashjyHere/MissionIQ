"""Company profile + capabilities."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

MATURITY_LEVELS = ("emerging", "developing", "mature", "market-leading")


class CompanyProfile(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "company_profile"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    legal_name: Mapped[str | None] = mapped_column(String(300))
    duns: Mapped[str | None] = mapped_column(String(32))
    uei: Mapped[str | None] = mapped_column(String(32))
    cage_code: Mapped[str | None] = mapped_column(String(32))
    primary_naics: Mapped[str | None] = mapped_column(String(16))
    size_standard: Mapped[str | None] = mapped_column(String(80))
    certifications: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    overview: Mapped[str | None] = mapped_column(Text)
    differentiators: Mapped[str | None] = mapped_column(Text)
    past_performance_summary: Mapped[str | None] = mapped_column(Text)

    workspace = relationship("Workspace", back_populates="company_profile")
    capabilities = relationship(
        "Capability", back_populates="company_profile", cascade="all, delete-orphan"
    )


class Capability(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "capability"
    __table_args__ = (
        CheckConstraint(f"maturity IN {MATURITY_LEVELS!r}", name="ck_capability_maturity"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    company_profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("company_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    maturity: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    evidence_links: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    company_profile = relationship("CompanyProfile", back_populates="capabilities")
