"""Apex Federal demo workspace — payload validation and constants."""
from __future__ import annotations

from app.intelligence import get_registry
from app.models.opportunity import CAPTURE_STAGES
from seeds.apex.constants import (
    DEMO_USERS,
    HISTORICAL_OUTCOMES,
    PROPOSAL_ASSETS,
    SHOWCASE_PURSUITS,
    WORKSPACE_SLUG,
    capture_stage_for_pursuit,
)
from seeds.apex.payloads import MODULE_BUILDERS, build_payload


def test_showcase_pursuit_portfolio():
    assert len(SHOWCASE_PURSUITS) == 6
    completed = [p for p in SHOWCASE_PURSUITS if p.outcome is not None]
    active = [p for p in SHOWCASE_PURSUITS if p.outcome is None]
    assert len(completed) == 4
    assert len(active) == 2
    assert sum(1 for p in SHOWCASE_PURSUITS if p.flagship) == 1


def test_showcase_capture_stages_are_valid():
    for pursuit in SHOWCASE_PURSUITS:
        assert pursuit.capture_stage in CAPTURE_STAGES
        assert pursuit.capture_stage not in {"won", "no_bid"}
        stage = capture_stage_for_pursuit(
            outcome=pursuit.outcome, active_stage=pursuit.capture_stage
        )
        assert stage in CAPTURE_STAGES


def test_historical_outcome_capture_stages_are_valid():
    for outcome in HISTORICAL_OUTCOMES:
        assert capture_stage_for_pursuit(outcome=outcome) in CAPTURE_STAGES


def test_historical_outcomes_match_target_metrics():
    assert len(HISTORICAL_OUTCOMES) == 38
    assert HISTORICAL_OUTCOMES.count("won") == 22
    assert HISTORICAL_OUTCOMES.count("lost") == 10
    assert HISTORICAL_OUTCOMES.count("no_bid") == 6


def test_proposal_asset_catalog_meets_minimum():
    assert len(PROPOSAL_ASSETS) >= 15
    types = {a["asset_type"] for a in PROPOSAL_ASSETS}
    assert "executive_summary" in types
    assert "win_theme" in types
    assert "transition_approach" in types
    assert "staffing_approach" in types
    assert "past_performance" in types
    assert "risk_mitigation" in types


def test_demo_users_have_distinct_roles():
    roles = {u["role"] for u in DEMO_USERS}
    assert roles == {"administrator", "approver", "reviewer", "contributor", "viewer"}
    assert len(DEMO_USERS) == 5


def test_intelligence_payloads_validate_against_schemas():
    registry = get_registry()
    for pursuit in SHOWCASE_PURSUITS:
        for module_id, _builder in MODULE_BUILDERS.items():
            payload = build_payload(module_id, pursuit)
            cls = registry.get(module_id)
            assert cls is not None
            if cls.output_model is not None:
                cls.output_model.model_validate(payload)


def test_workspace_slug():
    assert WORKSPACE_SLUG == "apex-federal"
