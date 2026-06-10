"""Governance model vocabularies + migration 0007 drift checks.

Mirrors test_outcome_models.py: the governance vocabularies, the append-only
table shapes, and the 0007 migration must agree, so drift is caught at
unit-test time. Also asserts the structural guarantee of the milestone:
nothing in the governance layer writes to ``ai_output``.
"""
from __future__ import annotations

import pathlib

from app.models.governance import (
    COMMENT_STATUSES,
    OVERRIDE_TYPES,
    REVIEW_ACTIONS,
    REVIEW_STATUSES,
    SIGNAL_TYPES,
    VALIDATION_STATUSES,
)

MIGRATION = pathlib.Path("alembic/versions/0007_collaboration_governance.py")


def test_vocabularies_match_milestone_contract():
    assert COMMENT_STATUSES == ("open", "resolved")
    assert REVIEW_STATUSES == ("draft", "in_review", "approved", "rejected", "archived")
    assert REVIEW_ACTIONS == ("submitted", "approved", "rejected", "reopened", "archived")
    assert OVERRIDE_TYPES == ("decision", "score")
    # "unvalidated" is the absence of judgment, not a stored status.
    assert VALIDATION_STATUSES == ("validated", "rejected")


def test_signal_types_cover_the_milestone_examples():
    assert set(SIGNAL_TYPES) == {
        "assumption_validated",
        "assumption_rejected",
        "decision_overridden",
        "score_overridden",
        "review_approved",
        "review_rejected",
        "comment_resolved",
    }


def test_override_reason_is_required_and_nonempty():
    from app.models import HumanOverride

    table = HumanOverride.__table__
    assert table.c.reason.nullable is False
    names = {c.name for c in table.constraints if c.name}
    assert "ck_override_reason_nonempty" in names


def test_override_preserves_original_and_adjusted_values():
    from app.models import HumanOverride

    cols = HumanOverride.__table__.c
    assert cols.original_value.nullable is False
    assert cols.override_value.nullable is False


def test_assumption_validation_snapshots_the_original_text():
    from app.models import AssumptionValidation

    cols = AssumptionValidation.__table__.c
    assert cols.assumption_text.nullable is False
    assert cols.assumption_key.nullable is False


def test_comment_supports_threads_mentions_and_resolution():
    from app.models import Comment

    cols = {c.name for c in Comment.__table__.c}
    assert {
        "parent_comment_id",
        "mentions",
        "status",
        "author_user_id",
        "resolved_by_user_id",
        "resolved_at",
    } <= cols


def test_migration_creates_all_governance_tables():
    src = MIGRATION.read_text()
    for table in (
        "comment",
        "deliverable_review",
        "review_event",
        "human_override",
        "assumption_validation",
        "governance_signal",
    ):
        assert f'"{table}"' in src, table
        assert f'op.drop_table("{table}")' in src, table


def _load_migration():
    import importlib.util

    spec = importlib.util.spec_from_file_location("migration_0007", MIGRATION)
    assert spec and spec.loader
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    return mig


def test_migration_constraints_match_models():
    mig = _load_migration()
    assert mig.COMMENT_STATUSES == COMMENT_STATUSES
    assert mig.REVIEW_STATUSES == REVIEW_STATUSES
    assert mig.REVIEW_ACTIONS == REVIEW_ACTIONS
    assert mig.OVERRIDE_TYPES == OVERRIDE_TYPES
    assert mig.VALIDATION_STATUSES == VALIDATION_STATUSES
    assert mig.SIGNAL_TYPES == SIGNAL_TYPES


def test_migration_role_vocabulary_matches_rbac():
    from app.core.rbac import ROLES

    mig = _load_migration()
    assert mig.ROLES == ROLES


def test_migration_does_not_touch_ai_output():
    """Structural guarantee: original AI intelligence is never modified."""
    src = MIGRATION.read_text()
    assert 'op.alter_column("ai_output"' not in src
    assert 'op.add_column("ai_output"' not in src
    assert 'op.drop_table("ai_output")' not in src


def test_governance_service_never_writes_ai_output():
    import inspect

    from app.services import governance_service

    source = inspect.getsource(governance_service)
    # AIOutput is read (latest generation lookups) but never constructed,
    # mutated, or deleted by the governance layer.
    assert "AIOutput(" not in source
    assert "db.delete(AIOutput" not in source
