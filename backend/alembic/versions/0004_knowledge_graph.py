"""knowledge graph: graph_entity + graph_edge

MissionIQ's institutional memory. Every intelligence module contributes
structured facts (entities + provenance-stamped edges) so the platform gets
smarter with every opportunity processed: similar opportunities, prior risks,
prior discriminators, and prior win themes become reusable across pursuits.

Revision ID: 0004_knowledge_graph
Revises: 0003_company_dna_fields
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_knowledge_graph"
down_revision = "0003_company_dna_fields"
branch_labels = None
depends_on = None

ENTITY_TYPES = (
    "agency",
    "program",
    "opportunity",
    "contract",
    "competitor",
    "technology",
    "capability",
    "risk",
    "win_theme",
    "discriminator",
    "contract_vehicle",
    "past_performance",
)

RELATION_TYPES = (
    "opportunity_for_agency",
    "opportunity_under_program",
    "opportunity_uses_vehicle",
    "opportunity_has_incumbent",
    "opportunity_has_competitor",
    "opportunity_has_risk",
    "opportunity_has_win_theme",
    "opportunity_has_discriminator",
    "opportunity_requires_capability",
    "opportunity_involves_technology",
    "company_has_capability",
    "company_has_past_performance",
)


def upgrade() -> None:
    op.create_table(
        "graph_entity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("normalized_key", sa.String(400), nullable=False),
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspace.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "entity_type",
            "normalized_key",
            name="uq_graph_entity_ws_type_key",
        ),
        sa.CheckConstraint(
            f"entity_type IN {ENTITY_TYPES!r}", name="ck_graph_entity_type"
        ),
    )
    op.create_index(
        "ix_graph_entity_ws_type", "graph_entity", ["workspace_id", "entity_type"]
    )

    op.create_table(
        "graph_edge",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(60), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("module_id", sa.String(80), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspace.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"], ["graph_entity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_entity_id"], ["graph_entity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            f"relation IN {RELATION_TYPES!r}", name="ck_graph_edge_relation"
        ),
    )
    op.create_index(
        "ix_graph_edge_ws_relation", "graph_edge", ["workspace_id", "relation"]
    )
    op.create_index("ix_graph_edge_opportunity", "graph_edge", ["opportunity_id"])
    op.create_index(
        "ix_graph_edge_provenance", "graph_edge", ["opportunity_id", "module_id"]
    )
    op.create_index("ix_graph_edge_source", "graph_edge", ["source_entity_id"])
    op.create_index("ix_graph_edge_target", "graph_edge", ["target_entity_id"])


def downgrade() -> None:
    op.drop_table("graph_edge")
    op.drop_table("graph_entity")
