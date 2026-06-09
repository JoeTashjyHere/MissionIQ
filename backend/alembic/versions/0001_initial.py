"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-09 10:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "identity_provider", sa.String(64), nullable=False, server_default="password"
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "refresh_token",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "rotated_to_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refresh_token.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_token_user", "refresh_token", ["user_id"])

    op.create_table(
        "workspace",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column(
            "settings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspace_slug", "workspace", ["slug"], unique=True)

    op.create_table(
        "team_member",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("invited_at", sa.DateTime(timezone=True)),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_team_member_ws_user"),
        sa.CheckConstraint(
            "role IN ('owner','admin','member','viewer')",
            name="ck_team_member_role",
        ),
    )
    op.create_index("ix_team_member_ws", "team_member", ["workspace_id"])
    op.create_index("ix_team_member_user", "team_member", ["user_id"])

    op.create_table(
        "opportunity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("agency", sa.String(200)),
        sa.Column("sub_agency", sa.String(200)),
        sa.Column("contract_vehicle", sa.String(200)),
        sa.Column("solicitation_number", sa.String(100)),
        sa.Column("naics_code", sa.String(16)),
        sa.Column("psc_code", sa.String(16)),
        sa.Column("set_aside", sa.String(80)),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("posted_date", sa.DateTime(timezone=True)),
        sa.Column("estimated_value_cents", sa.BigInteger()),
        sa.Column(
            "capture_stage",
            sa.String(40),
            nullable=False,
            server_default="identification",
        ),
        sa.Column("incumbent", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "capture_stage IN ('identification','qualification','pursue','capture',"
            "'proposal','submitted','awarded','lost','no-bid')",
            name="ck_opportunity_stage",
        ),
    )
    op.create_index("ix_opp_ws", "opportunity", ["workspace_id"])
    op.create_index("ix_opp_ws_stage", "opportunity", ["workspace_id", "capture_stage"])
    op.create_index("ix_opp_ws_due", "opportunity", ["workspace_id", "due_date"])
    op.create_index("ix_opp_ws_agency", "opportunity", ["workspace_id", "agency"])

    op.create_table(
        "document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("doc_type", sa.String(40), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("blob_key", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "doc_type IN ('rfp','rfi','sources_sought','pws','sow','soo','qasp',"
            "'sections_l_m','evaluation_criteria','past_performance','capture_notes',"
            "'internal_solution','other')",
            name="ck_document_type",
        ),
        sa.CheckConstraint(
            "status IN ('uploaded','extracting','chunking','embedding','ready','failed')",
            name="ck_document_status",
        ),
    )
    op.create_index("ix_doc_opp", "document", ["opportunity_id"])
    op.create_index("ix_doc_ws_opp", "document", ["workspace_id", "opportunity_id"])
    op.create_index("ix_doc_ws_sha", "document", ["workspace_id", "sha256"])

    op.create_table(
        "document_chunk",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("section_path", sa.String(300)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(1536)),
        sa.Column("embedding_model", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chunk_ws", "document_chunk", ["workspace_id"])
    op.create_index("ix_chunk_opp", "document_chunk", ["opportunity_id"])
    op.create_index(
        "ix_chunk_ws_doc_idx",
        "document_chunk",
        ["workspace_id", "document_id", "chunk_index"],
    )

    op.create_table(
        "market_intel_source",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("auth_mode", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "classification IN ('public','customer_licensed','customer_uploaded')",
            name="ck_mi_source_classification",
        ),
        sa.CheckConstraint(
            "auth_mode IN ('none','api_key','oauth','customer_credentials')",
            name="ck_mi_source_auth_mode",
        ),
    )

    op.create_table(
        "market_intel_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(64),
            sa.ForeignKey("market_intel_source.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
        ),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("agency", sa.String(200)),
        sa.Column("sub_agency", sa.String(200)),
        sa.Column("notice_type", sa.String(80)),
        sa.Column("naics_code", sa.String(16)),
        sa.Column("psc_code", sa.String(16)),
        sa.Column("set_aside", sa.String(80)),
        sa.Column("estimated_value_cents", sa.BigInteger()),
        sa.Column("posted_date", sa.DateTime(timezone=True)),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("incumbent", sa.String(200)),
        sa.Column(
            "raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_embedding", Vector(1536)),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_id", "external_id", "workspace_id", name="uq_mi_record_dedupe"
        ),
    )
    op.create_index(
        "ix_mi_record_source_ws_due",
        "market_intel_record",
        ["source_id", "workspace_id", "due_date"],
    )
    op.create_index("ix_mi_record_agency_due", "market_intel_record", ["agency", "due_date"])

    op.create_table(
        "opportunity_market_intel_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "market_intel_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_intel_record.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linked_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("relevance", sa.Numeric(4, 3)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "opportunity_id", "market_intel_record_id", name="uq_opp_mi_link"
        ),
    )
    op.create_index("ix_opp_mi_opp", "opportunity_market_intel_link", ["opportunity_id"])
    op.create_index("ix_opp_mi_rec", "opportunity_market_intel_link", ["market_intel_record_id"])

    op.create_table(
        "company_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("legal_name", sa.String(300)),
        sa.Column("duns", sa.String(32)),
        sa.Column("uei", sa.String(32)),
        sa.Column("cage_code", sa.String(32)),
        sa.Column("primary_naics", sa.String(16)),
        sa.Column("size_standard", sa.String(80)),
        sa.Column("certifications", postgresql.ARRAY(sa.String())),
        sa.Column("overview", sa.Text()),
        sa.Column("differentiators", sa.Text()),
        sa.Column("past_performance_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "capability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "company_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_profile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80)),
        sa.Column("maturity", sa.String(20)),
        sa.Column("description", sa.Text()),
        sa.Column("keywords", postgresql.ARRAY(sa.String())),
        sa.Column("evidence_links", postgresql.ARRAY(sa.String())),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "maturity IN ('emerging','developing','mature','market-leading') OR maturity IS NULL",
            name="ck_capability_maturity",
        ),
    )
    op.create_index("ix_cap_ws", "capability", ["workspace_id"])

    op.create_table(
        "ai_output",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
        ),
        sa.Column("module_id", sa.String(120), nullable=False),
        sa.Column("module_version", sa.String(20), nullable=False),
        sa.Column("prompt_id", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(20), nullable=False),
        sa.Column("model_provider", sa.String(40), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column(
            "output_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("evidence_chunk_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column(
            "evidence_market_record_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="ok"),
        sa.Column(
            "generated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('ok','insufficient_context','error')", name="ck_ai_output_status"
        ),
    )
    op.create_index(
        "ix_ai_output_ws_opp_module_created",
        "ai_output",
        ["workspace_id", "opportunity_id", "module_id", "created_at"],
    )

    op.create_table(
        "compliance_requirement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ai_output_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_output.id"),
        ),
        sa.Column("requirement_code", sa.String(80)),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document.id"),
        ),
        sa.Column("source_page", sa.Integer()),
        sa.Column("source_section", sa.String(200)),
        sa.Column("owner", sa.String(200)),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('open','in_progress','complete','n_a')",
            name="ck_compliance_status",
        ),
    )
    op.create_index("ix_compreq_opp", "compliance_requirement", ["opportunity_id"])

    op.create_table(
        "evaluation_criterion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ai_output_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_output.id"),
        ),
        sa.Column("factor", sa.String(200), nullable=False),
        sa.Column("subfactor", sa.String(200)),
        sa.Column("importance", sa.String(40)),
        sa.Column("required_response_elements", postgresql.ARRAY(sa.String())),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document.id"),
        ),
        sa.Column("source_page", sa.Integer()),
        sa.Column("source_section", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "importance IN ('most_important','important','less_important','equal','unspecified') OR importance IS NULL",
            name="ck_eval_importance",
        ),
    )
    op.create_index("ix_evalcrit_opp", "evaluation_criterion", ["opportunity_id"])

    op.create_table(
        "risk",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ai_output_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_output.id"),
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(40)),
        sa.Column("description", sa.Text()),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document.id"),
        ),
        sa.Column("source_page", sa.Integer()),
        sa.Column("impact", sa.String(20)),
        sa.Column("likelihood", sa.String(20)),
        sa.Column("mitigation", sa.Text()),
        sa.Column("owner", sa.String(200)),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "category IN ('technical','staffing','schedule','financial','security',"
            "'compliance','competitive','transition','other') OR category IS NULL",
            name="ck_risk_category",
        ),
        sa.CheckConstraint(
            "impact IN ('low','medium','high','critical') OR impact IS NULL",
            name="ck_risk_impact",
        ),
        sa.CheckConstraint(
            "likelihood IN ('low','medium','high') OR likelihood IS NULL",
            name="ck_risk_likelihood",
        ),
        sa.CheckConstraint(
            "status IN ('open','mitigated','accepted','closed')", name="ck_risk_status"
        ),
    )
    op.create_index("ix_risk_opp", "risk", ["opportunity_id"])

    op.create_table(
        "chat_thread",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity.id", ondelete="CASCADE"),
        ),
        sa.Column("title", sa.String(300)),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thread_ws", "chat_thread", ["workspace_id"])
    op.create_index("ix_thread_opp", "chat_thread", ["opportunity_id"])

    op.create_table(
        "chat_message",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_thread.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_chunk_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column(
            "evidence_market_record_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))
        ),
        sa.Column("model_provider", sa.String(40)),
        sa.Column("model_name", sa.String(120)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("status", sa.String(40), nullable=False, server_default="ok"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "role IN ('user','assistant','system')", name="ck_chat_message_role"
        ),
        sa.CheckConstraint(
            "status IN ('ok','insufficient_context','error')",
            name="ck_chat_message_status",
        ),
    )
    op.create_index("ix_msg_thread", "chat_message", ["thread_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
        ),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ip", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_ws_created", "audit_log", ["workspace_id", "created_at"])
    op.create_index("ix_audit_actor_created", "audit_log", ["actor_user_id", "created_at"])

    op.bulk_insert(
        sa.table(
            "market_intel_source",
            sa.column("id", sa.String),
            sa.column("display_name", sa.String),
            sa.column("classification", sa.String),
            sa.column("auth_mode", sa.String),
            sa.column("enabled", sa.Boolean),
        ),
        [
            {
                "id": "sam_gov",
                "display_name": "SAM.gov",
                "classification": "public",
                "auth_mode": "api_key",
                "enabled": True,
            },
            {
                "id": "govwin",
                "display_name": "GovWin IQ",
                "classification": "customer_licensed",
                "auth_mode": "customer_credentials",
                "enabled": False,
            },
            {
                "id": "salesforce",
                "display_name": "Salesforce",
                "classification": "customer_licensed",
                "auth_mode": "oauth",
                "enabled": False,
            },
            {
                "id": "sharepoint",
                "display_name": "SharePoint",
                "classification": "customer_licensed",
                "auth_mode": "oauth",
                "enabled": False,
            },
        ],
    )


def downgrade() -> None:
    for table in (
        "audit_log",
        "chat_message",
        "chat_thread",
        "risk",
        "evaluation_criterion",
        "compliance_requirement",
        "ai_output",
        "capability",
        "company_profile",
        "opportunity_market_intel_link",
        "market_intel_record",
        "market_intel_source",
        "document_chunk",
        "document",
        "opportunity",
        "team_member",
        "workspace",
        "refresh_token",
        "user",
    ):
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS citext")
    op.execute("DROP EXTENSION IF EXISTS vector")
