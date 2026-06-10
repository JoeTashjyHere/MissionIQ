"""Review workflow state machine tests.

Draft → In Review → Approved/Rejected (→ reopen/resubmit) → Archived, with
role capabilities per transition and append-only history semantics. The state
machine is a pure function, so every legal and illegal transition is pinned
here without a database.
"""
from __future__ import annotations

import pytest

from app.core.errors import ConflictError
from app.models.governance import (
    GOVERNED_MODULES,
    REVIEW_ACTIONS,
    REVIEW_STATUSES,
    REVIEWABLE_MODULES,
)
from app.services.governance_service import (
    REVIEW_TRANSITIONS,
    apply_review_action,
    decision_summary_for,
    review_capability,
)


def test_review_states_match_milestone_contract():
    assert REVIEW_STATUSES == ("draft", "in_review", "approved", "rejected", "archived")


def test_reviewable_deliverables_match_milestone_contract():
    assert REVIEWABLE_MODULES == (
        "capture.win_strategy",
        "capture.executive_brief",
        "capture.gate_review",
        "capture.bid_decision",
    )
    assert set(REVIEWABLE_MODULES) <= set(GOVERNED_MODULES)


def test_governed_modules_match_milestone_contract():
    assert set(GOVERNED_MODULES) == {
        "capture.customer_dna",
        "capture.company_dna",
        "capture.capability_match",
        "capture.win_strategy",
        "capture.executive_brief",
        "capture.gate_review",
        "capture.bid_decision",
        "capture.outcome_intelligence",
    }


def test_legal_transitions():
    assert apply_review_action("draft", "submit") == ("in_review", "submitted")
    assert apply_review_action("in_review", "approve") == ("approved", "approved")
    assert apply_review_action("in_review", "reject") == ("rejected", "rejected")
    assert apply_review_action("rejected", "submit") == ("in_review", "submitted")
    assert apply_review_action("approved", "reopen") == ("in_review", "reopened")
    assert apply_review_action("rejected", "reopen") == ("in_review", "reopened")
    for status in ("draft", "in_review", "approved", "rejected"):
        assert apply_review_action(status, "archive") == ("archived", "archived")


@pytest.mark.parametrize(
    ("status", "action"),
    [
        ("draft", "approve"),  # cannot approve without review
        ("draft", "reject"),
        ("draft", "reopen"),
        ("in_review", "submit"),  # already in review
        ("approved", "approve"),  # decisions are terminal until reopened
        ("approved", "reject"),
        ("approved", "submit"),
        ("rejected", "reject"),
        ("archived", "submit"),  # archived cycles are immutable
        ("archived", "approve"),
        ("archived", "reject"),
        ("archived", "reopen"),
        ("archived", "archive"),
    ],
)
def test_illegal_transitions_raise(status: str, action: str):
    with pytest.raises(ConflictError) as exc:
        apply_review_action(status, action)
    assert exc.value.code == "review.illegal_transition"


def test_unknown_action_raises():
    with pytest.raises(ConflictError) as exc:
        apply_review_action("draft", "promote")
    assert exc.value.code == "review.unknown_action"


def test_every_event_action_is_reachable():
    reachable = {spec[2] for spec in REVIEW_TRANSITIONS.values()}
    assert reachable == set(REVIEW_ACTIONS)


def test_transition_capabilities():
    # Submitting is a contributor act; deciding requires approver+.
    assert review_capability("submit") == "review.submit"
    assert review_capability("archive") == "review.submit"
    assert review_capability("approve") == "review.decide"
    assert review_capability("reject") == "review.decide"
    assert review_capability("reopen") == "review.decide"


def test_review_history_is_append_only_by_construction():
    """The service layer must expose no update/delete path for review events,
    overrides, validations, or signals — approvals are immutable records."""
    import inspect

    from app.services import governance_service

    source = inspect.getsource(governance_service)
    for table in ("ReviewEvent", "HumanOverride", "AssumptionValidation", "GovernanceSignal"):
        assert f"db.delete({table}" not in source
    names = [n for n, _ in inspect.getmembers(governance_service, inspect.isfunction)]
    assert not any(n.startswith(("delete_", "update_")) for n in names)


def test_decision_summary_snapshots_the_recommendation():
    summary = decision_summary_for(
        "capture.executive_brief",
        {
            "executive_recommendation": {
                "recommendation": "pursue_aggressively",
                "confidence_score": 78,
            }
        },
    )
    assert summary == "Pursue Aggressively · 78% confidence"


def test_decision_summary_handles_unknown_modules():
    assert decision_summary_for("capture.customer_dna", {"anything": 1}) is None
    assert decision_summary_for("capture.bid_decision", {}) is None
