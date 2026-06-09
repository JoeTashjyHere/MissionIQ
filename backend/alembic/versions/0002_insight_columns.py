"""insight-grade columns: compliance, evaluation, risk

Adds the columns the new consultant-grade modules need to write structured,
DNA-aware analysis back to the relational tables alongside the raw JSON in
``ai_output``. Storing the structured rows enables CSV exports, joined
queries (e.g. "risks tied to OIG concerns"), and traceability from a
compliance row back to the DNA attribute it laddered into.

Revision ID: 0002_insight_columns
Revises: 0001_initial
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_insight_columns"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Compliance Matrix: why / mission alignment / customer priority
    op.add_column(
        "compliance_requirement",
        sa.Column("category", sa.String(60), nullable=True),
    )
    op.add_column(
        "compliance_requirement",
        sa.Column("why_requirement_exists", sa.Text(), nullable=True),
    )
    op.add_column(
        "compliance_requirement",
        sa.Column("mission_alignment", sa.Text(), nullable=True),
    )
    op.add_column(
        "compliance_requirement",
        sa.Column("customer_priority", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_compliance_priority",
        "compliance_requirement",
        "customer_priority IN ('critical','high','medium','low') OR customer_priority IS NULL",
    )

    # Evaluation Criteria: insight payload
    op.add_column(
        "evaluation_criterion",
        sa.Column("evaluation_intelligence", sa.Text(), nullable=True),
    )
    op.add_column(
        "evaluation_criterion",
        sa.Column(
            "likely_decision_drivers",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "evaluation_criterion",
        sa.Column(
            "potential_discriminators",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "evaluation_criterion",
        sa.Column(
            "potential_weaknesses",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "evaluation_criterion",
        sa.Column(
            "strategic_recommendations",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )

    # Risk: mission impact + probability + severity + supporting evidence
    op.add_column(
        "risk",
        sa.Column("lane", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_risk_lane",
        "risk",
        "lane IN ('capture','proposal','delivery','customer') OR lane IS NULL",
    )
    op.add_column(
        "risk",
        sa.Column("mission_impact", sa.Text(), nullable=True),
    )
    op.add_column(
        "risk",
        sa.Column("probability", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_risk_probability",
        "risk",
        "probability IN ('low','medium','high') OR probability IS NULL",
    )
    op.add_column(
        "risk",
        sa.Column("severity", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_risk_severity",
        "risk",
        "severity IN ('low','medium','high','critical') OR severity IS NULL",
    )
    op.add_column(
        "risk",
        sa.Column(
            "supporting_evidence",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_risk_severity", "risk", type_="check")
    op.drop_constraint("ck_risk_probability", "risk", type_="check")
    op.drop_constraint("ck_risk_lane", "risk", type_="check")
    op.drop_column("risk", "supporting_evidence")
    op.drop_column("risk", "severity")
    op.drop_column("risk", "probability")
    op.drop_column("risk", "mission_impact")
    op.drop_column("risk", "lane")

    op.drop_column("evaluation_criterion", "strategic_recommendations")
    op.drop_column("evaluation_criterion", "potential_weaknesses")
    op.drop_column("evaluation_criterion", "potential_discriminators")
    op.drop_column("evaluation_criterion", "likely_decision_drivers")
    op.drop_column("evaluation_criterion", "evaluation_intelligence")

    op.drop_constraint("ck_compliance_priority", "compliance_requirement", type_="check")
    op.drop_column("compliance_requirement", "customer_priority")
    op.drop_column("compliance_requirement", "mission_alignment")
    op.drop_column("compliance_requirement", "why_requirement_exists")
    op.drop_column("compliance_requirement", "category")
