"""Workspace + TeamMember models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

ROLES = ("owner", "admin", "member", "viewer")


class Workspace(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "workspace"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    settings_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    members = relationship("TeamMember", back_populates="workspace", cascade="all, delete-orphan")
    opportunities = relationship(
        "Opportunity", back_populates="workspace", cascade="all, delete-orphan"
    )
    company_profile = relationship(
        "CompanyProfile",
        back_populates="workspace",
        cascade="all, delete-orphan",
        uselist=False,
    )


class TeamMember(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "team_member"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_team_member_ws_user"),
        CheckConstraint(f"role IN {ROLES!r}", name="ck_team_member_role"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")
