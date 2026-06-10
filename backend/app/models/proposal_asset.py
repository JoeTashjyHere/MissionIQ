"""Proposal Intelligence Repository models.

Organizations win because they possess knowledge, not because they possess
documents. ``proposal_asset`` decomposes proposal artifacts into structured,
reusable intelligence assets — each permanently linked to its source document,
enriched with outcome statistics, and searchable as institutional memory.

This is not a document management system. Chunks remain the retrieval substrate;
assets are the extracted, scored, reusable outputs.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

ASSET_TYPES = (
    "executive_summary",
    "win_theme",
    "staffing_approach",
    "transition_approach",
    "management_approach",
    "technical_approach",
    "past_performance",
    "risk_mitigation",
    "discriminator",
    "pricing_narrative",
    "lessons_learned",
    "custom",
)

# Document types that trigger automatic asset extraction after ingestion.
PROPOSAL_DOC_TYPES = ("proposal", "proposal_volume")

EXTRACTION_CONFIDENCE = ("high", "medium", "low")
EXTRACTION_BASIS = ("evidence", "inference", "assumption")

USAGE_KINDS = ("extracted_from", "referenced", "recommended", "manual")


class ProposalAsset(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "proposal_asset"
    __table_args__ = (
        CheckConstraint(f"asset_type IN {ASSET_TYPES!r}", name="ck_proposal_asset_type"),
        CheckConstraint(
            f"extraction_confidence IN {EXTRACTION_CONFIDENCE!r}",
            name="ck_proposal_asset_confidence",
        ),
        CheckConstraint(
            f"extraction_basis IN {EXTRACTION_BASIS!r}", name="ck_proposal_asset_basis"
        ),
        UniqueConstraint(
            "workspace_id", "normalized_key", name="uq_proposal_asset_ws_key"
        ),
        Index("ix_proposal_asset_ws_type", "workspace_id", "asset_type"),
        Index("ix_proposal_asset_ws_agency", "workspace_id", "agency"),
        Index("ix_proposal_asset_document", "document_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # Type-specific structured body (narrative, bullets, PP fields, …).
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Source connection is never optional — assets always trace to a document.
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="SET NULL")
    )
    agency: Mapped[str | None] = mapped_column(String(200))
    customer_name: Mapped[str | None] = mapped_column(String(200))
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Denormalized from pursuit_outcome; refreshed on outcome record/delete.
    outcome: Mapped[str | None] = mapped_column(String(20))
    author: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[str | None] = mapped_column(String(80))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user_upload")
    source_connector_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connector.id", ondelete="SET NULL")
    )
    source_external_id: Mapped[str | None] = mapped_column(String(200))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    extraction_confidence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )
    extraction_basis: Mapped[str] = mapped_column(
        String(20), nullable=False, default="evidence"
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    # Stable dedup identity: sha256(asset_type + normalized title) per workspace.
    normalized_key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Outcome stats — historical correlations only, never causal scores.
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    win_rate: Mapped[float | None] = mapped_column(Float)
    outcome_weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default="1.0"
    )

    citations = relationship(
        "ProposalAssetCitation",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    usages = relationship(
        "ProposalAssetUsage",
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class ProposalAssetUsage(UUIDPkMixin, Base):
    """Links an asset to a pursuit — the backbone of outcome linkage."""

    __tablename__ = "proposal_asset_usage"
    __table_args__ = (
        CheckConstraint(f"usage_kind IN {USAGE_KINDS!r}", name="ck_asset_usage_kind"),
        Index("ix_asset_usage_opp", "opportunity_id"),
        Index("ix_asset_usage_asset", "asset_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("proposal_asset.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset = relationship("ProposalAsset", back_populates="usages")


class ProposalAssetCitation(UUIDPkMixin, Base):
    """Supporting evidence — the asset never loses its source connection."""

    __tablename__ = "proposal_asset_citation"
    __table_args__ = (Index("ix_asset_citation_asset", "asset_id"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("proposal_asset.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_chunk.id", ondelete="SET NULL")
    )
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[str | None] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset = relationship("ProposalAsset", back_populates="citations")
