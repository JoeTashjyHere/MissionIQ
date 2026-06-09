"""Connector framework + pursuit automation models.

A *Connector* is a workspace-scoped instance of an integration provider
(Salesforce, SharePoint, Local Repository, …). Provider *behavior* lives in the
code-side registry (``app/connectors``); these tables store the instance
configuration, encrypted credentials, sync-job history, and automation runs.

State machines mirror the document-processing pattern (``DOC_STATUSES``):
explicit status vocabularies with CHECK constraints plus a progress map so the
UI can render the same StatusPill/ProgressBar experience users already trust.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

CONNECTOR_TYPES = (
    "crm",
    "document_repository",
    "market_intelligence",
    "project_management",
    "knowledge_management",
)

CONNECTOR_STATUSES = ("connected", "disconnected", "syncing", "failed", "disabled")

CREDENTIAL_TYPES = ("api_key", "oauth", "basic", "none")

SYNC_JOB_TRIGGERS = ("manual", "scheduled", "webhook", "automation")

SYNC_JOB_STATUSES = (
    "queued",
    "connecting",
    "discovering",
    "ingesting",
    "succeeded",
    "partial",
    "failed",
)

SYNC_JOB_PROGRESS: dict[str, int] = {
    "queued": 5,
    "connecting": 20,
    "discovering": 45,
    "ingesting": 75,
    "succeeded": 100,
    "partial": 100,
    "failed": 100,
}

AUTOMATION_TRIGGERS = ("connector", "manual")

AUTOMATION_STATUSES = ("queued", "running", "succeeded", "partial", "failed")

# Data provenance vocabulary shared by Opportunity and Document rows. The other
# three platform categories already carry their own provenance: market-intel
# records (public market intelligence), graph/memory items (historical memory),
# and AIOutput rows (generated intelligence).
SOURCE_TYPES = ("user_upload", "connector")


class Connector(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "connector"
    __table_args__ = (
        CheckConstraint(
            f"connector_type IN {CONNECTOR_TYPES!r}", name="ck_connector_type"
        ),
        CheckConstraint(
            f"status IN {CONNECTOR_STATUSES!r}", name="ck_connector_status"
        ),
        Index("ix_connector_ws_provider", "workspace_id", "provider_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[str] = mapped_column(String(60), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="disconnected"
    )
    # Non-secret provider configuration (folder paths, instance URLs, filters).
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Automation wiring: create pursuits from discovered opportunities, and
    # kick off the Pursuit Automation Orchestrator for newly created pursuits.
    auto_create_pursuits: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    auto_run_automation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )

    credential = relationship(
        "ConnectorCredential",
        back_populates="connector",
        cascade="all, delete-orphan",
        uselist=False,
    )
    sync_jobs = relationship(
        "ConnectorSyncJob", back_populates="connector", cascade="all, delete-orphan"
    )


class ConnectorCredential(UUIDPkMixin, TimestampMixin, Base):
    """Encrypted-at-rest secret for a connector. Never serialized to the API —
    responses expose only ``credential_set`` / ``credential_type`` /
    ``last_validated_at`` derived fields."""

    __tablename__ = "connector_credential"
    __table_args__ = (
        CheckConstraint(
            f"credential_type IN {CREDENTIAL_TYPES!r}",
            name="ck_connector_credential_type",
        ),
        UniqueConstraint("connector_id", name="uq_connector_credential_connector"),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("connector.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none"
    )
    secret_encrypted: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    connector = relationship("Connector", back_populates="credential")


class ConnectorSyncJob(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "connector_sync_job"
    __table_args__ = (
        CheckConstraint(
            f"trigger IN {SYNC_JOB_TRIGGERS!r}", name="ck_sync_job_trigger"
        ),
        CheckConstraint(
            f"status IN {SYNC_JOB_STATUSES!r}", name="ck_sync_job_status"
        ),
        Index("ix_sync_job_ws_created", "workspace_id", "created_at"),
        Index("ix_sync_job_connector_created", "connector_id", "created_at"),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("connector.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # items_discovered / opportunities_created / opportunities_updated /
    # documents_ingested / items_skipped / items_failed
    stats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )

    connector = relationship("Connector", back_populates="sync_jobs")


class AutomationRun(UUIDPkMixin, TimestampMixin, Base):
    """One execution of the Pursuit Automation Orchestrator for a pursuit.

    ``steps`` is the ordered, auditable record of the declarative step plan:
    a list of ``{step_id, label, status, attempts, started_at, finished_at,
    error, ai_output_id}`` dicts. Retry re-runs from the first failed step.
    """

    __tablename__ = "automation_run"
    __table_args__ = (
        CheckConstraint(
            f"trigger IN {AUTOMATION_TRIGGERS!r}", name="ck_automation_trigger"
        ),
        CheckConstraint(
            f"status IN {AUTOMATION_STATUSES!r}", name="ck_automation_status"
        ),
        Index("ix_automation_ws_created", "workspace_id", "created_at"),
        Index("ix_automation_opp_created", "opportunity_id", "created_at"),
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
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    current_step: Mapped[str | None] = mapped_column(String(60))
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("user.id")
    )
    connector_sync_job_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connector_sync_job.id", ondelete="SET NULL")
    )
