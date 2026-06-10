"""Outcome Intelligence math — the deterministic core of the learning loop.

Pure-function tests for outcome weighting, recommendation extraction,
alignment rules, calibration bucketing, and entity outcome records. These
functions are the honesty contract: every number is an observed statistic.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.outcome_intelligence_service import (
    build_calibration,
    build_factor_frequencies,
    compute_alignment,
    compute_entity_outcome_records,
    compute_win_rate,
    extract_recommendation,
    laplace_weight,
)

# ── Weighting math ─────────────────────────────────────────────────────────


def test_win_rate_is_none_until_a_decided_pursuit_exists():
    assert compute_win_rate(0, 0) is None
    assert compute_win_rate(3, 1) == 0.75
    assert compute_win_rate(0, 2) == 0.0


def test_laplace_weight_is_smoothed_and_centered_on_no_signal():
    # No signal → exactly 0.5.
    assert laplace_weight(0, 0) == 0.5
    # A single win must NOT produce a perfect weight (small-sample damping).
    assert laplace_weight(1, 0) == pytest.approx(2 / 3)
    assert laplace_weight(1, 0) < 1.0
    # Symmetric for losses.
    assert laplace_weight(0, 1) == pytest.approx(1 / 3)
    # Converges toward the raw rate with more data.
    assert laplace_weight(9, 1) == pytest.approx(10 / 12)
    assert abs(laplace_weight(9, 1) - 0.9) < abs(laplace_weight(1, 0) - 1.0)


# ── Recommendation extraction ──────────────────────────────────────────────


def test_extract_recommendation_per_module():
    bid = extract_recommendation(
        "capture.bid_decision",
        {"recommendation": "bid", "confidence": {"score": 61}},
    )
    assert bid.recommendation_type == "bid_decision"
    assert bid.predicted_label == "bid"

    gate = extract_recommendation(
        "capture.gate_review",
        {
            "decision_recommendation": "pursue",
            "probability_of_win": {"score": 60},
        },
    )
    assert gate.recommendation_type == "gate_recommendation"
    assert gate.predicted_label == "pursue"
    assert gate.predicted_score == 60

    ws = extract_recommendation(
        "capture.win_strategy",
        {
            "pursuit_recommendation": "pursue_with_conditions",
            "win_confidence_assessment": {"score": 58},
        },
    )
    assert ws.recommendation_type == "win_confidence"
    assert ws.predicted_score == 58

    eb = extract_recommendation(
        "capture.executive_brief",
        {
            "executive_recommendation": {
                "recommendation": "pursue_aggressively",
                "confidence_score": 70,
            }
        },
    )
    assert eb.recommendation_type == "executive_recommendation"
    assert eb.predicted_label == "pursue_aggressively"


def test_extract_recommendation_unknown_module_or_empty_output():
    assert extract_recommendation("capture.customer_dna", {"mission": "x"}) is None
    assert extract_recommendation("capture.bid_decision", {}) is None


# ── Alignment rules (correlation, never causation) ─────────────────────────


def test_alignment_bid_recommendations():
    # Recommended bid + won → aligned.
    assert compute_alignment("bid_decision", "bid", None, "won") is True
    # Recommended bid + lost → not aligned.
    assert compute_alignment("bid_decision", "bid", None, "lost") is False
    # Recommended no_bid + pursued anyway + lost → aligned (bid discipline).
    assert compute_alignment("bid_decision", "no_bid", None, "lost") is True
    # Recommended no_bid + org no-bid → aligned.
    assert compute_alignment("bid_decision", "no_bid", None, "no_bid") is True
    assert compute_alignment("bid_decision", "bid", None, "no_bid") is False


def test_alignment_undefined_for_non_competitive_ends():
    assert compute_alignment("bid_decision", "bid", None, "cancelled") is None
    assert compute_alignment("win_confidence", None, 80.0, "withdrawn") is None


def test_alignment_win_confidence_uses_score():
    assert compute_alignment("win_confidence", "pursue", 70.0, "won") is True
    assert compute_alignment("win_confidence", "pursue", 70.0, "lost") is False
    assert compute_alignment("win_confidence", "pursue", 30.0, "lost") is True
    # Score-only predictions say nothing about a no-bid decision.
    assert compute_alignment("win_confidence", None, 70.0, "no_bid") is None


def test_alignment_executive_labels():
    assert (
        compute_alignment("executive_recommendation", "monitor", None, "lost") is True
    )
    assert (
        compute_alignment(
            "executive_recommendation", "pursue_with_conditions", None, "won"
        )
        is True
    )


def test_alignment_none_when_nothing_predictive():
    assert compute_alignment("bid_decision", None, None, "won") is None


# ── Entity outcome records ─────────────────────────────────────────────────


def _edge(opp_id, src, tgt):
    return SimpleNamespace(
        opportunity_id=opp_id, source_entity_id=src, target_entity_id=tgt
    )


def test_entity_records_count_decided_pursuits_only_and_distinctly():
    won_opp, lost_opp, nobid_opp = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    theme = uuid.uuid4()
    opp_node = uuid.uuid4()

    edges = [
        _edge(won_opp, opp_node, theme),
        _edge(won_opp, opp_node, theme),  # duplicate edge — same pursuit
        _edge(lost_opp, opp_node, theme),
        _edge(nobid_opp, opp_node, theme),  # no_bid is NOT decided
        _edge(None, opp_node, theme),  # no provenance → ignored
    ]
    outcomes = {won_opp: "won", lost_opp: "lost", nobid_opp: "no_bid"}
    records = compute_entity_outcome_records(edges, outcomes)

    assert records[theme] == {won_opp: "won", lost_opp: "lost"}
    wins = sum(1 for o in records[theme].values() if o == "won")
    losses = sum(1 for o in records[theme].values() if o == "lost")
    assert (wins, losses) == (1, 1)


# ── Calibration ────────────────────────────────────────────────────────────


def test_calibration_buckets_and_observed_rates():
    scored = [
        (30.0, "won"),
        (35.0, "lost"),
        (65.0, "won"),
        (70.0, "won"),
        (75.0, "lost"),
        (90.0, "won"),
        (50.0, "no_bid"),  # not decided → excluded
    ]
    buckets = {b.range_label: b for b in build_calibration(scored)}
    assert buckets["0–40"].predictions == 2
    assert buckets["0–40"].observed_win_rate == 0.5
    assert buckets["40–60"].predictions == 0
    assert buckets["40–60"].observed_win_rate is None
    assert buckets["60–80"].predictions == 3
    assert buckets["60–80"].observed_wins == 2
    assert buckets["80–100"].predictions == 1
    assert buckets["80–100"].observed_win_rate == 1.0


# ── Debrief factor frequencies ─────────────────────────────────────────────


def test_factor_frequencies_split_wins_and_losses():
    from app.models import PursuitOutcome

    outcomes = [
        PursuitOutcome(outcome="won", outcome_factors=["Price", "Transition"]),
        PursuitOutcome(outcome="lost", outcome_factors=["price"]),
        PursuitOutcome(outcome="lost", outcome_factors=["Price"]),
        PursuitOutcome(outcome="no_bid", outcome_factors=["Price"]),  # ignored
    ]
    rows = {f.factor.lower(): f for f in build_factor_frequencies(outcomes)}
    assert rows["price"].in_wins == 1
    assert rows["price"].in_losses == 2
    assert rows["transition"].in_wins == 1
