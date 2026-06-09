"""Document + DocumentChunk models. Chunks hold embeddings via pgvector."""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

DOC_TYPES = (
    "rfp",
    "rfi",
    "sources_sought",
    "pws",
    "sow",
    "soo",
    "qasp",
    "sections_l_m",
    "evaluation_criteria",
    "past_performance",
    "capture_notes",
    "internal_solution",
    "other",
)

DOC_STATUSES = ("uploaded", "parsing", "chunking", "embedding", "ready", "failed")

DOC_STATUS_PROGRESS: dict[str, int] = {
    "uploaded": 5,
    "parsing": 25,
    "chunking": 50,
    "embedding": 75,
    "ready": 100,
    "failed": 100,
}


class Document(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "document"
    __table_args__ = (
        CheckConstraint(f"doc_type IN {DOC_TYPES!r}", name="ck_document_type"),
        CheckConstraint(f"status IN {DOC_STATUSES!r}", name="ck_document_status"),
        CheckConstraint(
            "source_type IN ('user_upload', 'connector')",
            name="ck_document_source_type",
        ),
        Index("ix_doc_ws_opp", "workspace_id", "opportunity_id"),
        Index("ix_doc_ws_sha", "workspace_id", "sha256"),
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
        index=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blob_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Data provenance: who put this document into MissionIQ.
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user_upload", server_default="user_upload"
    )
    source_connector_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connector.id", ondelete="SET NULL")
    )
    source_external_id: Mapped[str | None] = mapped_column(String(200))

    opportunity = relationship("Opportunity", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "document_chunk"
    __table_args__ = (
        Index("ix_chunk_ws_doc_idx", "workspace_id", "document_id", "chunk_index"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[str | None] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(120))

    document = relationship("Document", back_populates="chunks")
