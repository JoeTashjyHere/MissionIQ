"""seller-side company profile fields (Company DNA source of truth)

Adds the structured seller-side fields that power the Company DNA module and
the Capability Matching engine: contract vehicles, technology partners,
case studies, key personnel / SMEs, geographic footprint, security posture,
delivery model, and pricing / cost-positioning notes. Core capabilities and
past performance already live in the ``capability`` table and the existing
``past_performance_summary`` column respectively.

Revision ID: 0003_company_dna_fields
Revises: 0002_insight_columns
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_company_dna_fields"
down_revision = "0002_insight_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_profile",
        sa.Column(
            "contract_vehicles",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "company_profile",
        sa.Column(
            "technology_partners",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "company_profile", sa.Column("case_studies", sa.Text(), nullable=True)
    )
    op.add_column(
        "company_profile", sa.Column("key_personnel", sa.Text(), nullable=True)
    )
    op.add_column(
        "company_profile",
        sa.Column("geographic_footprint", sa.Text(), nullable=True),
    )
    op.add_column(
        "company_profile", sa.Column("security_posture", sa.Text(), nullable=True)
    )
    op.add_column(
        "company_profile", sa.Column("delivery_model", sa.Text(), nullable=True)
    )
    op.add_column(
        "company_profile", sa.Column("pricing_posture", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("company_profile", "pricing_posture")
    op.drop_column("company_profile", "delivery_model")
    op.drop_column("company_profile", "security_posture")
    op.drop_column("company_profile", "geographic_footprint")
    op.drop_column("company_profile", "key_personnel")
    op.drop_column("company_profile", "case_studies")
    op.drop_column("company_profile", "technology_partners")
    op.drop_column("company_profile", "contract_vehicles")
