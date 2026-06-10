"""Win/loss patterns, strategic observations, and memory track records.

Locks the epistemic honesty contract: pattern and observation language is
descriptive (observed patterns / historical correlations with supporting
evidence) and NEVER causal.
"""
from __future__ import annotations

import uuid

from app.schemas.outcome import (
    FactorFrequency,
    OutcomePattern,
    OutcomeSummary,
    RecommendationPerformance,
    SourcePursuit,
)
from app.services.memory_service import (
    AggregatedItem,
    ItemOccurrence,
    _to_memory_item,
    aggregate_memory_items,
    format_track_record,
)
from app.services.outcome_intelligence_service import (
    build_strategic_observations,
    observation_text,
)

CAUSAL_PHRASES = ("because", "caused", "causes", "leads to", "led to", "due to")


def _pattern(label: str, etype: str, wins: int, losses: int, **kw) -> OutcomePattern:
    from app.services.outcome_intelligence_service import (
        compute_win_rate,
        laplace_weight,
    )

    return OutcomePattern(
        label=label,
        entity_type=etype,
        wins=wins,
        losses=losses,
        win_rate=compute_win_rate(wins, losses),
        outcome_weight=laplace_weight(wins, losses),
        observation=observation_text(label, wins, losses),
        source_pursuits=[
            SourcePursuit(id=uuid.uuid4(), name=f"Pursuit {i}", outcome="won")
            for i in range(wins + losses)
        ],
        **kw,
    )


def test_observation_text_is_descriptive_not_causal():
    text = observation_text("Zero-downtime transition", 3, 1)
    assert "3 won" in text and "1 lost" in text
    assert "75% historical win rate" in text
    for phrase in CAUSAL_PHRASES:
        assert phrase not in text.lower()


def test_strategic_observations_carry_evidence_and_avoid_causal_language():
    summary = OutcomeSummary(
        recorded=5,
        decided=4,
        wins=3,
        losses=1,
        win_rate=0.75,
        no_bids=1,
        value_won_cents=1_000_000_00,
        recommendation_alignment_rate=0.8,
    )
    observations = build_strategic_observations(
        summary=summary,
        win_patterns=[_pattern("Mission continuity", "win_theme", 3, 0)],
        loss_patterns=[_pattern("Transition timeline", "risk", 0, 2)],
        agency_trends=[_pattern("Defense Health Agency", "agency", 3, 1)],
        competitor_trends=[
            _pattern("Acme Federal", "competitor", 0, 2, awards_taken=2)
        ],
        factor_frequencies=[FactorFrequency(factor="price", in_wins=0, in_losses=3)],
        performance=[
            RecommendationPerformance(
                recommendation_type="bid_decision",
                module_id="capture.bid_decision",
                total=4,
                aligned=3,
                alignment_rate=0.75,
            )
        ],
    )
    assert observations, "expected observations from a populated history"
    joined = " ".join(o.observation for o in observations).lower()
    for phrase in CAUSAL_PHRASES:
        assert phrase not in joined, f"causal phrase {phrase!r} leaked into output"
    # Every observation is classified and evidence-cited.
    for o in observations:
        assert o.kind in ("observed_pattern", "historical_correlation")
        assert o.sources, f"observation lacks supporting evidence: {o.observation}"
    # The recommendation-performance line explicitly disclaims causation.
    perf_lines = [o for o in observations if "alignment" in o.observation.lower() or "aligned" in o.observation.lower()]
    assert any("not a causal" in o.observation for o in perf_lines)


def test_no_observations_without_history():
    summary = OutcomeSummary(
        recorded=0,
        decided=0,
        wins=0,
        losses=0,
        win_rate=None,
        no_bids=0,
        value_won_cents=0,
        recommendation_alignment_rate=None,
    )
    assert (
        build_strategic_observations(
            summary=summary,
            win_patterns=[],
            loss_patterns=[],
            agency_trends=[],
            competitor_trends=[],
            factor_frequencies=[],
            performance=[],
        )
        == []
    )


# ── Memory track records ───────────────────────────────────────────────────


def test_format_track_record():
    assert format_track_record(0, 0, None) is None
    assert format_track_record(3, 1, 0.75) == "3W–1L · 75% historical win rate"
    assert format_track_record(0, 2, 0.0) == "0W–2L · 0% historical win rate"


def test_memory_item_carries_track_record():
    agg = AggregatedItem(
        label="Zero-downtime transition",
        entity_type="win_theme",
        basis="historical",
        frequency=2,
        sources=[(uuid.uuid4(), "Prior pursuit")],
        attributes={},
        wins=2,
        losses=1,
        win_rate=2 / 3,
        outcome_weight=0.6,
    )
    item = _to_memory_item(agg)
    assert item.track_record == "2W–1L · 67% historical win rate"
    assert item.wins == 2 and item.losses == 1


def test_aggregation_breaks_frequency_ties_by_outcome_weight():
    current = uuid.uuid4()
    prior_a, prior_b = uuid.uuid4(), uuid.uuid4()

    def occ(label: str, opp: uuid.UUID, weight: float, wins: int, losses: int):
        return ItemOccurrence(
            label=label,
            entity_type="win_theme",
            opportunity_id=opp,
            opportunity_name="Prior",
            wins=wins,
            losses=losses,
            win_rate=None,
            outcome_weight=weight,
        )

    items = aggregate_memory_items(
        [
            occ("Unproven theme", prior_a, 0.5, 0, 0),
            occ("Proven theme", prior_b, 0.8, 3, 0),
        ],
        current_opportunity_id=current,
    )
    # Same frequency (1 prior pursuit each) — the proven item must rank first.
    assert [i.label for i in items] == ["Proven theme", "Unproven theme"]
