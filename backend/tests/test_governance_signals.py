"""Governance signal collection tests.

Human judgment becomes institutional-memory signals — validated assumptions,
overrides, review decisions, resolved comments. Per the milestone, signals
are collected and stored ONLY: recommendation logic, prompts, and Knowledge
Graph weighting must not consume them yet.
"""
from __future__ import annotations

import uuid

from app.models import GovernanceSignal
from app.models.governance import SIGNAL_TYPES
from app.services.governance_service import _emit_signal


class _CollectingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def test_emit_signal_appends_a_signal_row():
    db = _CollectingSession()
    ws = uuid.uuid4()
    opp = uuid.uuid4()
    actor = uuid.uuid4()
    _emit_signal(
        db,  # type: ignore[arg-type]
        workspace_id=ws,
        signal_type="assumption_validated",
        subject="Incumbent staff will transition.",
        opportunity_id=opp,
        module_id="capture.win_strategy",
        actor_user_id=actor,
        payload={"assumption_key": "abc"},
    )
    assert len(db.added) == 1
    signal = db.added[0]
    assert isinstance(signal, GovernanceSignal)
    assert signal.workspace_id == ws
    assert signal.signal_type == "assumption_validated"
    assert signal.subject == "Incumbent staff will transition."
    assert signal.module_id == "capture.win_strategy"
    assert signal.payload == {"assumption_key": "abc"}


def test_emit_signal_defaults_payload_to_empty_dict():
    db = _CollectingSession()
    _emit_signal(
        db,  # type: ignore[arg-type]
        workspace_id=uuid.uuid4(),
        signal_type="comment_resolved",
        subject="thread",
        opportunity_id=None,
        module_id=None,
        actor_user_id=None,
    )
    assert db.added[0].payload == {}


def test_every_emitted_signal_type_is_in_the_vocabulary():
    """Every signal_type literal the service can emit must pass the model's
    CHECK constraint vocabulary."""
    import inspect

    from app.services import governance_service

    source = inspect.getsource(governance_service)
    # Static literals.
    for literal in ("comment_resolved",):
        assert literal in SIGNAL_TYPES
        assert literal in source
    # f-string families: review_{approved,rejected}, {decision,score}_overridden,
    # assumption_{validated,rejected}.
    for emitted in (
        "review_approved",
        "review_rejected",
        "decision_overridden",
        "score_overridden",
        "assumption_validated",
        "assumption_rejected",
    ):
        assert emitted in SIGNAL_TYPES


def test_signals_are_not_consumed_by_recommendation_logic_yet():
    """The milestone is explicit: collect and store only. Nothing in the
    intelligence/memory/graph layers may read GovernanceSignal."""
    import inspect

    from app.intelligence import base as intelligence_base
    from app.services import (
        intelligence_service,
        memory_service,
        outcome_intelligence_service,
    )

    for module in (
        intelligence_base,
        intelligence_service,
        memory_service,
        outcome_intelligence_service,
    ):
        source = inspect.getsource(module)
        assert "GovernanceSignal" not in source, module.__name__


def test_audit_action_vocabulary_for_governance():
    """Every milestone audit action must appear in the service/API source so
    each governed act creates a reconstructable audit record."""
    import inspect

    from app.api.v1 import workspaces
    from app.services import governance_service

    service_src = inspect.getsource(governance_service)
    workspaces_src = inspect.getsource(workspaces)
    for action in (
        "comment.created",
        "comment.replied",
        "comment.resolved",
        "comment.reopened",
        "decision.overridden",
        "score.overridden",
    ):
        assert action in service_src, action
    # review.{submitted,approved,rejected,reopened,archived} via f-string.
    assert 'f"review.{event_action}"' in service_src
    # assumption.{validated,rejected} via f-string.
    assert 'f"assumption.{payload.status}"' in service_src
    assert "member.role_changed" in workspaces_src
