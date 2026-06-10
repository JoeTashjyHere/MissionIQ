"""collaboration & governance: RBAC roles + comments, reviews, overrides, validations, signals

MissionIQ generates intelligence; humans make decisions. This revision adds
the governance layer:

- ``team_member.role`` vocabulary migrates to the five-role hierarchy
  (viewer < contributor < reviewer < approver < administrator). Mapping is
  deterministic: owner/admin -> administrator, member -> contributor,
  viewer -> viewer. Workspace ownership itself is preserved by
  ``workspace.owner_user_id``; the downgrade maps administrator -> admin and
  contributor -> member (the owner/admin distinction is intentionally lossy).
- Six new tables: ``comment``, ``deliverable_review``, ``review_event``
  (append-only approval ledger), ``human_override`` (append-only decision /
  score ledger), ``assumption_validation`` (append-only), and
  ``governance_signal`` (append-only institutional-memory signals).

Nothing touches ``ai_output`` — original AI intelligence is never modified.

Revision ID: 0007_collaboration_governance
Revises: 0006_outcome_intelligence
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_collaboration_governance"
down_revision = "0006_outcome_intelligence"
branch_labels = None
depends_on = None

ROLES = ("viewer", "contributor", "reviewer", "approver", "administrator")
LEGACY_ROLES = ("owner", "admin", "member", "viewer")

COMMENT_STATUSES = ("open", "resolved")
REVIEW_STATUSES = ("draft", "in_review", "approved", "rejected", "archived")
REVIEW_ACTIONS = ("submitted", "approved", "rejected", "reopened", "archived")
OVERRIDE_TYPES = ("decision", "score")
VALIDATION_STATUSES = ("validated", "rejected")
SIGNAL_TYPES = (
    "assumption_validated",
    "assumption_rejected",
    "decision_overridden",
    "score_overridden",
    "review_approved",
    "review_rejected",
    "comment_resolved",
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
    # ── RBAC: migrate team_member.role to the governance hierarchy ──────────
    op.drop_constraint("ck_team_member_role", "team_member", type_="check")
    op.execute(
        """
        UPDATE team_member SET role = CASE role
            WHEN 'owner' THEN 'administrator'
            WHEN 'admin' THEN 'administrator'
            WHEN 'member' THEN 'contributor'
            ELSE role
        END
        """
    )
    op.alter_column("team_member", "role", server_default="contributor")
    op.create_check_constraint(
        "ck_team_member_role", "team_member", f"role IN {ROLES!r}"
    )

    # ── Comments ─────────────────────────────────────────────────────────────
    op.create_table(
        "comment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_module_id", sa.String(120), nullable=False),
        sa.Column("ai_output_id", postgresql.UUID(as_uuid=True)),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ai_output_id"], ["ai_output.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"], ["comment.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["user.id"]),
        sa.CheckConstraint(f"status IN {COMMENT_STATUSES!r}", name="ck_comment_status"),
    )
    op.create_index(
        "ix_comment_opp_module", "comment", ["opportunity_id", "target_module_id"]
    )

    # ── Review workflow ──────────────────────────────────────────────────────
    op.create_table(
        "deliverable_review",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", sa.String(120), nullable=False),
        sa.Column("ai_output_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ai_output_id"], ["ai_output.id"], ondelete="SET NULL"),
        sa.CheckConstraint(f"status IN {REVIEW_STATUSES!r}", name="ck_review_status"),
    )
    op.create_index(
        "ix_review_opp_module", "deliverable_review", ["opportunity_id", "module_id"]
    )

    op.create_table(
        "review_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("decision_summary", sa.String(300)),
        sa.Column("notes", sa.Text()),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["deliverable_review.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.CheckConstraint(
            f"action IN {REVIEW_ACTIONS!r}", name="ck_review_event_action"
        ),
    )
    op.create_index(
        "ix_review_event_review", "review_event", ["review_id", "created_at"]
    )

    # ── Human overrides (decision ledger + feedback capture) ────────────────
    op.create_table(
        "human_override",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_output_id", postgresql.UUID(as_uuid=True)),
        sa.Column("module_id", sa.String(120), nullable=False),
        sa.Column("override_type", sa.String(20), nullable=False),
        sa.Column("field", sa.String(200), nullable=False),
        sa.Column("original_value", postgresql.JSONB(), nullable=False),
        sa.Column("override_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ai_output_id"], ["ai_output.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.CheckConstraint(
            f"override_type IN {OVERRIDE_TYPES!r}", name="ck_override_type"
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0", name="ck_override_reason_nonempty"
        ),
    )
    op.create_index(
        "ix_override_opp_module", "human_override", ["opportunity_id", "module_id"]
    )
    op.create_index(
        "ix_override_ws_created", "human_override", ["workspace_id", "created_at"]
    )

    # ── Assumption validation ────────────────────────────────────────────────
    op.create_table(
        "assumption_validation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_output_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", sa.String(120), nullable=False),
        sa.Column("assumption_key", sa.String(64), nullable=False),
        sa.Column("assumption_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("validator_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ai_output_id"], ["ai_output.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validator_user_id"], ["user.id"]),
        sa.CheckConstraint(
            f"status IN {VALIDATION_STATUSES!r}", name="ck_validation_status"
        ),
    )
    op.create_index(
        "ix_validation_output_key",
        "assumption_validation",
        ["ai_output_id", "assumption_key"],
    )
    op.create_index(
        "ix_validation_opp_module",
        "assumption_validation",
        ["opportunity_id", "module_id"],
    )

    # ── Governance signals (collected only — not consumed yet) ──────────────
    op.create_table(
        "governance_signal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("module_id", sa.String(120)),
        sa.Column("signal_type", sa.String(40), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.CheckConstraint(f"signal_type IN {SIGNAL_TYPES!r}", name="ck_signal_type"),
    )
    op.create_index(
        "ix_signal_ws_type", "governance_signal", ["workspace_id", "signal_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_signal_ws_type", table_name="governance_signal")
    op.drop_table("governance_signal")

    op.drop_index("ix_validation_opp_module", table_name="assumption_validation")
    op.drop_index("ix_validation_output_key", table_name="assumption_validation")
    op.drop_table("assumption_validation")

    op.drop_index("ix_override_ws_created", table_name="human_override")
    op.drop_index("ix_override_opp_module", table_name="human_override")
    op.drop_table("human_override")

    op.drop_index("ix_review_event_review", table_name="review_event")
    op.drop_table("review_event")

    op.drop_index("ix_review_opp_module", table_name="deliverable_review")
    op.drop_table("deliverable_review")

    op.drop_index("ix_comment_opp_module", table_name="comment")
    op.drop_table("comment")

    op.drop_constraint("ck_team_member_role", "team_member", type_="check")
    op.execute(
        """
        UPDATE team_member SET role = CASE role
            WHEN 'administrator' THEN 'admin'
            WHEN 'contributor' THEN 'member'
            WHEN 'reviewer' THEN 'member'
            WHEN 'approver' THEN 'admin'
            ELSE role
        END
        """
    )
    op.alter_column("team_member", "role", server_default="member")
    op.create_check_constraint(
        "ck_team_member_role", "team_member", f"role IN {LEGACY_ROLES!r}"
    )
