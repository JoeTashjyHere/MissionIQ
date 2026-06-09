"""connectors + pursuit automation + data provenance

The connector framework (connector / connector_credential / connector_sync_job),
the Pursuit Automation Orchestrator (automation_run), and provenance columns on
opportunity + document so every piece of information identifies its source.

Purely additive: new tables, plus defaulted columns on existing tables — every
existing row remains valid with zero backfill.

Revision ID: 0005_connectors_automation
Revises: 0004_knowledge_graph
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_connectors_automation"
down_revision = "0004_knowledge_graph"
branch_labels = None
depends_on = None

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
AUTOMATION_TRIGGERS = ("connector", "manual")
AUTOMATION_STATUSES = ("queued", "running", "succeeded", "partial", "failed")
SOURCE_TYPES = ("user_upload", "connector")


def upgrade() -> None:
    op.create_table(
        "connector",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(60), nullable=False),
        sa.Column("connector_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="disconnected"
        ),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "auto_create_pursuits",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_run_automation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.CheckConstraint(
            f"connector_type IN {CONNECTOR_TYPES!r}", name="ck_connector_type"
        ),
        sa.CheckConstraint(
            f"status IN {CONNECTOR_STATUSES!r}", name="ck_connector_status"
        ),
    )
    op.create_index("ix_connector_workspace_id", "connector", ["workspace_id"])
    op.create_index(
        "ix_connector_ws_provider", "connector", ["workspace_id", "provider_id"]
    )

    op.create_table(
        "connector_credential",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "credential_type", sa.String(20), nullable=False, server_default="none"
        ),
        sa.Column("secret_encrypted", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_validated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["connector.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            f"credential_type IN {CREDENTIAL_TYPES!r}",
            name="ck_connector_credential_type",
        ),
        sa.UniqueConstraint("connector_id", name="uq_connector_credential_connector"),
    )
    op.create_index(
        "ix_connector_credential_workspace_id", "connector_credential", ["workspace_id"]
    )

    op.create_table(
        "connector_sync_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "stats",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["connector.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["user.id"]),
        sa.CheckConstraint(
            f"trigger IN {SYNC_JOB_TRIGGERS!r}", name="ck_sync_job_trigger"
        ),
        sa.CheckConstraint(
            f"status IN {SYNC_JOB_STATUSES!r}", name="ck_sync_job_status"
        ),
    )
    op.create_index(
        "ix_sync_job_ws_created", "connector_sync_job", ["workspace_id", "created_at"]
    )
    op.create_index(
        "ix_sync_job_connector_created",
        "connector_sync_job",
        ["connector_id", "created_at"],
    )

    op.create_table(
        "automation_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("current_step", sa.String(60)),
        sa.Column(
            "steps",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("connector_sync_job_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(
            ["connector_sync_job_id"], ["connector_sync_job.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            f"trigger IN {AUTOMATION_TRIGGERS!r}", name="ck_automation_trigger"
        ),
        sa.CheckConstraint(
            f"status IN {AUTOMATION_STATUSES!r}", name="ck_automation_status"
        ),
    )
    op.create_index(
        "ix_automation_ws_created", "automation_run", ["workspace_id", "created_at"]
    )
    op.create_index(
        "ix_automation_opp_created", "automation_run", ["opportunity_id", "created_at"]
    )

    # ── Data provenance on existing tables ──────────────────────────────────
    for table in ("opportunity", "document"):
        op.add_column(
            table,
            sa.Column(
                "source_type",
                sa.String(20),
                nullable=False,
                server_default="user_upload",
            ),
        )
        op.add_column(
            table,
            sa.Column("source_connector_id", postgresql.UUID(as_uuid=True)),
        )
        op.add_column(table, sa.Column("source_external_id", sa.String(200)))
        op.create_foreign_key(
            f"fk_{table}_source_connector",
            table,
            "connector",
            ["source_connector_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_check_constraint(
            f"ck_{table}_source_type",
            table,
            f"source_type IN {SOURCE_TYPES!r}",
        )

    op.create_index(
        "uq_opp_connector_external",
        "opportunity",
        ["workspace_id", "source_connector_id", "source_external_id"],
        unique=True,
        postgresql_where=sa.text("source_connector_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_opp_connector_external", table_name="opportunity")
    for table in ("opportunity", "document"):
        op.drop_constraint(f"ck_{table}_source_type", table, type_="check")
        op.drop_constraint(f"fk_{table}_source_connector", table, type_="foreignkey")
        op.drop_column(table, "source_external_id")
        op.drop_column(table, "source_connector_id")
        op.drop_column(table, "source_type")

    op.drop_index("ix_automation_opp_created", table_name="automation_run")
    op.drop_index("ix_automation_ws_created", table_name="automation_run")
    op.drop_table("automation_run")

    op.drop_index("ix_sync_job_connector_created", table_name="connector_sync_job")
    op.drop_index("ix_sync_job_ws_created", table_name="connector_sync_job")
    op.drop_table("connector_sync_job")

    op.drop_index(
        "ix_connector_credential_workspace_id", table_name="connector_credential"
    )
    op.drop_table("connector_credential")

    op.drop_index("ix_connector_ws_provider", table_name="connector")
    op.drop_index("ix_connector_workspace_id", table_name="connector")
    op.drop_table("connector")
