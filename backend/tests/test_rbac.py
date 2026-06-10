"""RBAC capability layer contract tests.

The Collaboration & Governance milestone defines five workspace roles in a
strict hierarchy. These tests pin the role vocabulary, the hierarchy order,
the capability table, the legacy-role migration mapping, and the structured
403 raised when a capability is denied.
"""
from __future__ import annotations

import pytest

from app.core.errors import ForbiddenError
from app.core.rbac import (
    CAPABILITIES,
    LEGACY_ROLE_MAP,
    ROLES,
    has_capability,
    normalize_role,
    require_capability,
)


def test_roles_match_milestone_contract():
    # viewer < contributor < reviewer < approver < administrator
    assert ROLES == ("viewer", "contributor", "reviewer", "approver", "administrator")


def test_model_role_vocabulary_matches_rbac():
    from app.models.workspace import ROLES as MODEL_ROLES

    assert MODEL_ROLES == ROLES


def test_every_capability_maps_to_a_known_role():
    for capability, minimum in CAPABILITIES.items():
        assert minimum in ROLES, capability


def test_hierarchy_is_inclusive_upward():
    # Each role can do everything every lower role can do.
    for capability in CAPABILITIES:
        allowed = [role for role in ROLES if has_capability(role, capability)]
        # Allowed roles must be a contiguous suffix of the hierarchy.
        assert allowed == list(ROLES[len(ROLES) - len(allowed) :]), capability


def test_viewer_cannot_mutate_anything():
    for capability in CAPABILITIES:
        assert not has_capability("viewer", capability), capability


def test_administrator_can_do_everything():
    for capability in CAPABILITIES:
        assert has_capability("administrator", capability), capability


def test_governance_capability_minimums():
    # The milestone's governance acts assert organizational truth → approver+.
    assert not has_capability("reviewer", "review.decide")
    assert has_capability("approver", "review.decide")
    assert not has_capability("reviewer", "decision.override")
    assert has_capability("approver", "decision.override")
    assert not has_capability("reviewer", "assumption.validate")
    assert has_capability("approver", "assumption.validate")
    # Contributors collaborate: generate, comment, submit for review.
    assert has_capability("contributor", "intelligence.generate")
    assert has_capability("contributor", "comment.create")
    assert has_capability("contributor", "review.submit")
    # Team management is administrator-only.
    assert not has_capability("approver", "member.manage")
    assert has_capability("administrator", "member.manage")


def test_legacy_role_mapping_is_deterministic():
    # Migration 0007 mapping: owner/admin → administrator, member → contributor.
    assert LEGACY_ROLE_MAP == {
        "owner": "administrator",
        "admin": "administrator",
        "member": "contributor",
    }
    assert normalize_role("owner") == "administrator"
    assert normalize_role("admin") == "administrator"
    assert normalize_role("member") == "contributor"
    assert normalize_role("viewer") == "viewer"
    # Idempotent on new vocabulary.
    for role in ROLES:
        assert normalize_role(role) == role


def test_legacy_roles_still_resolve_capabilities():
    assert has_capability("owner", "member.manage")
    assert has_capability("member", "comment.create")
    assert not has_capability("member", "review.decide")


def test_unknown_role_has_no_capabilities():
    assert not has_capability("superuser", "comment.create")


def test_unknown_capability_raises():
    with pytest.raises(KeyError):
        has_capability("administrator", "does.not.exist")


def test_require_capability_raises_structured_403():
    with pytest.raises(ForbiddenError) as exc:
        require_capability("contributor", "review.decide")
    assert exc.value.code == "rbac.capability_denied"
    # No exception for a sufficient role.
    require_capability("approver", "review.decide")


def test_migration_0007_role_mapping_matches_rbac():
    """The SQL CASE in migration 0007 must agree with LEGACY_ROLE_MAP."""
    import pathlib

    src = pathlib.Path("alembic/versions/0007_collaboration_governance.py").read_text()
    assert "WHEN 'owner' THEN 'administrator'" in src
    assert "WHEN 'admin' THEN 'administrator'" in src
    assert "WHEN 'member' THEN 'contributor'" in src
