"""Outcome Intelligence model vocabularies + migration drift checks.

Mirrors test_connector_sync_states.py: the outcome vocabularies, the
recommendation types, the Knowledge Graph outcome columns, and the 0006
migration must agree, so drift is caught at unit-test time.
"""
from __future__ import annotations

from app.models.outcome import DECIDED_OUTCOMES, OUTCOMES, RECOMMENDATION_TYPES


def test_outcomes_match_milestone_contract():
    assert OUTCOMES == ("won", "lost", "no_bid", "cancelled", "withdrawn")


def test_decided_outcomes_are_competitive_results_only():
    # no_bid / cancelled / withdrawn are lifecycle ends, not decided
    # competitions — they must never count toward win/loss statistics.
    assert DECIDED_OUTCOMES == ("won", "lost")
    assert set(DECIDED_OUTCOMES) <= set(OUTCOMES)


def test_recommendation_types():
    assert set(RECOMMENDATION_TYPES) == {
        "bid_decision",
        "gate_recommendation",
        "win_confidence",
        "executive_recommendation",
    }


def test_pursuit_outcome_is_unique_per_opportunity():
    from app.models import PursuitOutcome

    uniques = [
        c for c in PursuitOutcome.__table__.constraints if c.name and "uq_" in c.name
    ]
    assert any(
        [col.name for col in u.columns] == ["opportunity_id"] for u in uniques
    )


def test_graph_entity_carries_outcome_weighting_columns():
    from app.models import GraphEntity

    cols = GraphEntity.__table__.columns
    assert {"wins", "losses", "win_rate", "outcome_weight"} <= {c.name for c in cols}
    # "No signal" defaults: 0/0, NULL rate, neutral weight.
    assert cols["wins"].default.arg == 0
    assert cols["losses"].default.arg == 0
    assert cols["win_rate"].nullable is True
    assert cols["outcome_weight"].default.arg == 1.0


def test_recommendation_outcome_alignment_is_nullable():
    """`aligned` must be nullable: alignment is undefined for cancelled /
    withdrawn pursuits and the schema documents it as a historical
    correlation, never a causal accuracy measure."""
    from app.models import RecommendationOutcome

    assert RecommendationOutcome.__table__.columns["aligned"].nullable is True


def test_migration_matches_model_vocabularies():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0006_outcome_intelligence.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0006", path)
    assert spec and spec.loader
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert mig.OUTCOMES == OUTCOMES
    assert mig.RECOMMENDATION_TYPES == RECOMMENDATION_TYPES
