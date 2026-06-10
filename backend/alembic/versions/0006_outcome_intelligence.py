"""outcome intelligence: pursuit_outcome + recommendation_outcome + graph weighting

The closed-loop learning layer. ``pursuit_outcome`` records what actually
happened to a pursuit; ``recommendation_outcome`` snapshots MissionIQ's
recommendations against the recorded outcome (alignment — a historical
correlation, never causation); ``graph_entity`` gains wins / losses /
win_rate / outcome_weight so institutional memory carries track records.

Purely additive. Existing graph entities default to the "no signal yet"
state (0 wins, 0 losses, NULL win_rate, weight 1.0) — no backfill needed.

Revision ID: 0006_outcome_intelligence
Revises: 0005_connectors_automation
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_outcome_intelligence"
down_revision = "0005_connectors_automation"
branch_labels = None
depends_on = None

OUTCOMES = ("won", "lost", "no_bid", "cancelled", "withdrawn")
RECOMMENDATION_TYPES = (
    "bid_decision",
    "gate_recommendation",
    "win_confidence",
    "executive_recommendation",
)


def upgrade() -> None:
    op.create_table(
        "pursuit_outcome",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("awarded_value_cents", sa.BigInteger()),
        sa.Column("awarded_to_competitor", sa.String(200)),
        sa.Column("outcome_factors", postgresql.ARRAY(sa.String())),
        sa.Column("debrief_notes", sa.Text()),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True)),
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
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["user.id"]),
        sa.CheckConstraint(f"outcome IN {OUTCOMES!r}", name="ck_pursuit_outcome"),
        sa.UniqueConstraint("opportunity_id", name="uq_pursuit_outcome_opportunity"),
    )
    op.create_index(
        "ix_pursuit_outcome_ws_outcome", "pursuit_outcome", ["workspace_id", "outcome"]
    )

    op.create_table(
        "recommendation_outcome",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pursuit_outcome_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_output_id", postgresql.UUID(as_uuid=True)),
        sa.Column("module_id", sa.String(120), nullable=False),
        sa.Column("recommendation_type", sa.String(40), nullable=False),
        sa.Column("predicted_label", sa.String(80)),
        sa.Column("predicted_score", sa.Float()),
        sa.Column("aligned", sa.Boolean()),
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
        sa.ForeignKeyConstraint(
            ["pursuit_outcome_id"], ["pursuit_outcome.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ai_output_id"], ["ai_output.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            f"recommendation_type IN {RECOMMENDATION_TYPES!r}",
            name="ck_recommendation_type",
        ),
    )
    op.create_index(
        "ix_rec_outcome_ws_type",
        "recommendation_outcome",
        ["workspace_id", "recommendation_type"],
    )
    op.create_index(
        "ix_rec_outcome_opportunity", "recommendation_outcome", ["opportunity_id"]
    )

    # ── Knowledge Graph outcome weighting ───────────────────────────────────
    op.add_column(
        "graph_entity",
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "graph_entity",
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("graph_entity", sa.Column("win_rate", sa.Float()))
    op.add_column(
        "graph_entity",
        sa.Column(
            "outcome_weight", sa.Float(), nullable=False, server_default="1.0"
        ),
    )


def downgrade() -> None:
    op.drop_column("graph_entity", "outcome_weight")
    op.drop_column("graph_entity", "win_rate")
    op.drop_column("graph_entity", "losses")
    op.drop_column("graph_entity", "wins")

    op.drop_index("ix_rec_outcome_opportunity", table_name="recommendation_outcome")
    op.drop_index("ix_rec_outcome_ws_type", table_name="recommendation_outcome")
    op.drop_table("recommendation_outcome")

    op.drop_index("ix_pursuit_outcome_ws_outcome", table_name="pursuit_outcome")
    op.drop_table("pursuit_outcome")
