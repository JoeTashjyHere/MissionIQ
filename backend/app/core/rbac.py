"""Role-based access control — the governance capability layer.

MissionIQ generates intelligence; humans make decisions. Who may make which
decision is expressed here as a single, easily-extended mapping:

- ``ROLES`` is a strict hierarchy (each role includes everything below it):
  viewer < contributor < reviewer < approver < administrator
- ``CAPABILITIES`` maps a named capability to the minimum role that holds it.
  Routes and services never compare roles directly — they ask for a
  capability, so future RBAC expansion is a dict entry, not a refactor.

Role assignments live on ``team_member.role`` (workspace-scoped).
"""
from __future__ import annotations

from app.core.errors import ForbiddenError

ROLES = ("viewer", "contributor", "reviewer", "approver", "administrator")

_RANK = {role: rank for rank, role in enumerate(ROLES)}

# Pre-governance role vocabulary → governance roles. Used by migration 0007
# and tolerated defensively at runtime.
LEGACY_ROLE_MAP = {
    "owner": "administrator",
    "admin": "administrator",
    "member": "contributor",
}

# Capability → minimum role. Everything not listed here is readable by any
# workspace member (viewer+); listing is only required for mutations.
CAPABILITIES = {
    # Intelligence generation
    "intelligence.generate": "contributor",
    "outcome.record": "contributor",
    # Collaboration
    "comment.create": "contributor",
    "comment.resolve": "contributor",
    # Review workflow: anyone who contributes may submit for review;
    # reviewers may record review notes; final approve/reject is approver+.
    "review.submit": "contributor",
    "review.note": "reviewer",
    "review.decide": "approver",
    # Governance judgments assert organizational truth → approver+.
    "decision.override": "approver",
    "assumption.validate": "approver",
    # Administration
    "member.manage": "administrator",
    "workspace.manage": "administrator",
}


def normalize_role(role: str) -> str:
    """Map legacy vocabulary onto the governance hierarchy (idempotent)."""
    return LEGACY_ROLE_MAP.get(role, role)


def has_capability(role: str, capability: str) -> bool:
    minimum = CAPABILITIES.get(capability)
    if minimum is None:
        raise KeyError(f"Unknown capability: {capability}")
    rank = _RANK.get(normalize_role(role))
    if rank is None:
        return False
    return rank >= _RANK[minimum]


def require_capability(role: str, capability: str) -> None:
    """Raise the platform's structured 403 when the role lacks a capability."""
    if not has_capability(role, capability):
        minimum = CAPABILITIES[capability]
        raise ForbiddenError(
            f"This action requires the '{minimum}' role or higher "
            f"(your role: '{normalize_role(role)}').",
            code="rbac.capability_denied",
        )
