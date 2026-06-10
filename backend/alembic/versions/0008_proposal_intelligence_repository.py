"""proposal intelligence repository: proposal_asset + usage + citation + graph vocab

Decomposes proposal documents into reusable intelligence assets — not a file
repository. Purely additive except extending document.doc_type and graph
entity/relation CHECK constraints.

Revision ID: 0008_proposal_intelligence_repository
Revises: 0007_collaboration_governance
"""
from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_proposal_intelligence_repository"
down_revision = "0007_collaboration_governance"
branch_labels = None
depends_on = None

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
EXTRACTION_CONFIDENCE = ("high", "medium", "low")
EXTRACTION_BASIS = ("evidence", "inference", "assumption")
USAGE_KINDS = ("extracted_from", "referenced", "recommended", "manual")

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
    "proposal",
    "proposal_volume",
    "other",
)

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
    "proposal_asset",
    "staffing_narrative",
    "transition_narrative",
    "executive_summary",
    "risk_mitigation",
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
    "agency_uses_proposal_asset",
    "proposal_asset_supports_win_theme",
    "proposal_asset_linked_capability",
    "proposal_asset_from_opportunity",
    "opportunity_used_asset",
)


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    # ── proposal_asset ───────────────────────────────────────────────────────
    op.create_table(
        "proposal_asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(40), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("agency", sa.String(200)),
        sa.Column("customer_name", sa.String(200)),
        sa.Column("submission_date", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.String(20)),
        sa.Column("author", sa.String(200)),
        sa.Column("version", sa.String(80)),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="user_upload"),
        sa.Column("source_connector_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_external_id", sa.String(200)),
        sa.Column("tags", postgresql.ARRAY(sa.String())),
        sa.Column("extraction_confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("extraction_basis", sa.String(20), nullable=False, server_default="evidence"),
        sa.Column("embedding", Vector(1536)),
        sa.Column("embedding_model", sa.String(120)),
        sa.Column("normalized_key", sa.String(64), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float()),
        sa.Column("outcome_weight", sa.Float(), nullable=False, server_default="1.0"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunity.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_connector_id"], ["connector.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(f"asset_type IN {ASSET_TYPES!r}", name="ck_proposal_asset_type"),
        sa.CheckConstraint(
            f"extraction_confidence IN {EXTRACTION_CONFIDENCE!r}",
            name="ck_proposal_asset_confidence",
        ),
        sa.CheckConstraint(
            f"extraction_basis IN {EXTRACTION_BASIS!r}", name="ck_proposal_asset_basis"
        ),
        sa.UniqueConstraint("workspace_id", "normalized_key", name="uq_proposal_asset_ws_key"),
    )
    op.create_index(
        "ix_proposal_asset_ws_type", "proposal_asset", ["workspace_id", "asset_type"]
    )
    op.create_index(
        "ix_proposal_asset_ws_agency", "proposal_asset", ["workspace_id", "agency"]
    )
    op.create_index("ix_proposal_asset_document", "proposal_asset", ["document_id"])

    op.create_table(
        "proposal_asset_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usage_kind", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["proposal_asset.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(f"usage_kind IN {USAGE_KINDS!r}", name="ck_asset_usage_kind"),
    )
    op.create_index("ix_asset_usage_opp", "proposal_asset_usage", ["opportunity_id"])
    op.create_index("ix_asset_usage_asset", "proposal_asset_usage", ["asset_id"])

    op.create_table(
        "proposal_asset_citation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True)),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("section_path", sa.String(300)),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["proposal_asset.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunk.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_asset_citation_asset", "proposal_asset_citation", ["asset_id"]
    )

    # ── document.doc_type vocabulary ─────────────────────────────────────────
    op.drop_constraint("ck_document_type", "document", type_="check")
    op.create_check_constraint("ck_document_type", "document", f"doc_type IN {DOC_TYPES!r}")

    # ── Knowledge Graph vocabulary ─────────────────────────────────────────────
    op.drop_constraint("ck_graph_entity_type", "graph_entity", type_="check")
    op.create_check_constraint(
        "ck_graph_entity_type", "graph_entity", f"entity_type IN {ENTITY_TYPES!r}"
    )
    op.drop_constraint("ck_graph_edge_relation", "graph_edge", type_="check")
    op.create_check_constraint(
        "ck_graph_edge_relation", "graph_edge", f"relation IN {RELATION_TYPES!r}"
    )


def downgrade() -> None:
    op.drop_constraint("ck_graph_edge_relation", "graph_edge", type_="check")
    op.create_check_constraint(
        "ck_graph_edge_relation",
        "graph_edge",
        "relation IN ('opportunity_for_agency', 'opportunity_under_program', "
        "'opportunity_uses_vehicle', 'opportunity_has_incumbent', "
        "'opportunity_has_competitor', 'opportunity_has_risk', "
        "'opportunity_has_win_theme', 'opportunity_has_discriminator', "
        "'opportunity_requires_capability', 'opportunity_involves_technology', "
        "'company_has_capability', 'company_has_past_performance')",
    )
    op.drop_constraint("ck_graph_entity_type", "graph_entity", type_="check")
    op.create_check_constraint(
        "ck_graph_entity_type",
        "graph_entity",
        "entity_type IN ('agency', 'program', 'opportunity', 'contract', "
        "'competitor', 'technology', 'capability', 'risk', 'win_theme', "
        "'discriminator', 'contract_vehicle', 'past_performance')",
    )

    op.drop_constraint("ck_document_type", "document", type_="check")
    op.create_check_constraint(
        "ck_document_type",
        "document",
        "doc_type IN ('rfp','rfi','sources_sought','pws','sow','soo','qasp',"
        "'sections_l_m','evaluation_criteria','past_performance','capture_notes',"
        "'internal_solution','other')",
    )

    op.drop_index("ix_asset_citation_asset", table_name="proposal_asset_citation")
    op.drop_table("proposal_asset_citation")
    op.drop_index("ix_asset_usage_asset", table_name="proposal_asset_usage")
    op.drop_index("ix_asset_usage_opp", table_name="proposal_asset_usage")
    op.drop_table("proposal_asset_usage")
    op.drop_index("ix_proposal_asset_document", table_name="proposal_asset")
    op.drop_index("ix_proposal_asset_ws_agency", table_name="proposal_asset")
    op.drop_index("ix_proposal_asset_ws_type", table_name="proposal_asset")
    op.drop_table("proposal_asset")
