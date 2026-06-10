"""Outcome Intelligence service — the closed-loop learning layer.

Two responsibilities:

1. **Outcome capture side effects.** Recording a ``PursuitOutcome`` moves the
   pursuit's lifecycle stage, snapshots ``RecommendationOutcome`` rows (what
   MissionIQ recommended at the time vs. what happened), and recomputes
   Knowledge Graph outcome weighting so institutional memory carries track
   records into every future pursuit.

2. **Deterministic workspace analysis.** Win/loss patterns, agency /
   capability / competitor trends, recommendation performance, and win-
   confidence calibration are pure statistics computed from recorded
   outcomes + the provenance-stamped graph. Every number carries its source
   pursuits.

Epistemic honesty contract: everything produced here is an *observed
pattern* or *historical correlation* with supporting evidence. No function
in this module asserts causation, and observation text is generated from
descriptive templates only.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.graph import normalize_key
from app.graph import service as graph_service
from app.models import (
    AIOutput,
    GraphEdge,
    GraphEntity,
    Opportunity,
    PursuitOutcome,
    RecommendationOutcome,
)
from app.models.outcome import DECIDED_OUTCOMES
from app.schemas.outcome import (
    CalibrationBucket,
    FactorFrequency,
    OutcomeIntelligenceReport,
    OutcomePattern,
    OutcomeRecordRequest,
    OutcomeSummary,
    RecommendationPerformance,
    SourcePursuit,
    StrategicObservation,
)
from app.services.audit_service import write_audit

# Outcome → terminal capture stage. cancelled / withdrawn have no dedicated
# stage, so the lifecycle stage is left untouched for them.
OUTCOME_TO_STAGE = {"won": "awarded", "lost": "lost", "no_bid": "no-bid"}

# Module → recommendation type and how to read its latest output.
RECOMMENDATION_SOURCES = {
    "capture.bid_decision": "bid_decision",
    "capture.gate_review": "gate_recommendation",
    "capture.win_strategy": "win_confidence",
    "capture.executive_brief": "executive_recommendation",
}

# Labels expressing intent to pursue vs. stand down.
_PURSUE_LABELS = frozenset(
    {"bid", "conditional_bid", "pursue", "pursue_with_conditions", "pursue_aggressively"}
)
_NO_PURSUE_LABELS = frozenset({"no_bid", "monitor"})


# ── Pure: outcome weighting math ───────────────────────────────────────────


def compute_win_rate(wins: int, losses: int) -> float | None:
    decided = wins + losses
    if decided == 0:
        return None
    return wins / decided


def laplace_weight(wins: int, losses: int) -> float:
    """Laplace-smoothed win rate: (wins+1)/(wins+losses+2).

    Range (0, 1) with 0.5 meaning "no signal". The smoothing keeps a single
    lucky win from dominating — a 1W/0L entity weighs 0.667, not 1.0. This is
    a historical correlation prior, never a causal score.
    """
    return (wins + 1) / (wins + losses + 2)


# ── Pure: recommendation extraction + alignment ────────────────────────────


@dataclass
class RecommendationSnapshot:
    module_id: str
    recommendation_type: str
    predicted_label: str | None
    predicted_score: float | None


def extract_recommendation(module_id: str, output: dict) -> RecommendationSnapshot | None:
    """Pull the recommendation (label and/or score) out of a module output."""
    rec_type = RECOMMENDATION_SOURCES.get(module_id)
    if rec_type is None or not isinstance(output, dict):
        return None
    label: str | None = None
    score: float | None = None
    if rec_type == "bid_decision":
        label = output.get("recommendation")
        conf = output.get("confidence") or {}
        score = conf.get("score") if isinstance(conf, dict) else None
    elif rec_type == "gate_recommendation":
        label = output.get("decision_recommendation")
        pwin = output.get("probability_of_win") or {}
        score = pwin.get("score") if isinstance(pwin, dict) else None
    elif rec_type == "win_confidence":
        label = output.get("pursuit_recommendation")
        wca = output.get("win_confidence_assessment") or {}
        score = wca.get("score") if isinstance(wca, dict) else None
    elif rec_type == "executive_recommendation":
        rec = output.get("executive_recommendation") or {}
        if isinstance(rec, dict):
            label = rec.get("recommendation")
            score = rec.get("confidence_score")
    if label is None and score is None:
        return None
    return RecommendationSnapshot(
        module_id=module_id,
        recommendation_type=rec_type,
        predicted_label=label,
        predicted_score=float(score) if score is not None else None,
    )


def compute_alignment(
    recommendation_type: str,
    predicted_label: str | None,
    predicted_score: float | None,
    outcome: str,
) -> bool | None:
    """Did the recommendation align with the recorded outcome?

    Alignment is a historical correlation, never a causal accuracy claim.
    Returns None when alignment is undefined (cancelled / withdrawn pursuits,
    or score-only recommendations against a no-bid outcome).
    """
    if outcome in ("cancelled", "withdrawn"):
        return None

    pursue: bool | None = None
    if recommendation_type == "win_confidence" and predicted_score is not None:
        # Confidence scores are read as predicted-win-probability statements.
        pursue = predicted_score >= 50
    elif predicted_label in _PURSUE_LABELS:
        pursue = True
    elif predicted_label in _NO_PURSUE_LABELS:
        pursue = False
    elif predicted_score is not None:
        pursue = predicted_score >= 50

    if pursue is None:
        return None
    if outcome == "won":
        return pursue
    if outcome == "lost":
        return not pursue
    if outcome == "no_bid":
        # A no-bid recommendation aligned with the org's decision to stand
        # down; score-only predictions say nothing about bid discipline.
        if predicted_label in _PURSUE_LABELS or predicted_label in _NO_PURSUE_LABELS:
            return not pursue
        return None
    return None


# ── Pure: entity outcome statistics ────────────────────────────────────────


def compute_entity_outcome_records(
    edges: list[GraphEdge],
    outcome_by_opp: dict[uuid.UUID, str],
) -> dict[uuid.UUID, dict[uuid.UUID, str]]:
    """For each graph entity, the decided pursuits it was linked to.

    Returns ``{entity_id: {opportunity_id: outcome}}`` considering only
    decided (won / lost) pursuits — no_bid / cancelled / withdrawn are
    lifecycle ends, not competitive results.
    """
    records: dict[uuid.UUID, dict[uuid.UUID, str]] = defaultdict(dict)
    for e in edges:
        if e.opportunity_id is None:
            continue
        outcome = outcome_by_opp.get(e.opportunity_id)
        if outcome not in DECIDED_OUTCOMES:
            continue
        records[e.source_entity_id][e.opportunity_id] = outcome
        records[e.target_entity_id][e.opportunity_id] = outcome
    return dict(records)


def observation_text(label: str, wins: int, losses: int) -> str:
    """Descriptive, never causal."""
    rate = compute_win_rate(wins, losses)
    rate_txt = f" ({round(rate * 100)}% historical win rate)" if rate is not None else ""
    return (
        f"'{label}' appeared in {wins} won and {losses} lost pursuit(s){rate_txt}."
    )


def build_calibration(
    scored: list[tuple[float, str]],
) -> list[CalibrationBucket]:
    """Bucket win-confidence predictions against observed outcomes."""
    buckets = [(0, 40), (40, 60), (60, 80), (80, 101)]
    out: list[CalibrationBucket] = []
    for lo, hi in buckets:
        rows = [(s, o) for s, o in scored if lo <= s < hi and o in DECIDED_OUTCOMES]
        n = len(rows)
        wins = sum(1 for _, o in rows if o == "won")
        out.append(
            CalibrationBucket(
                range_label=f"{lo}–{min(hi, 100)}",
                predictions=n,
                observed_wins=wins,
                observed_win_rate=round(wins / n, 3) if n else None,
                avg_predicted_score=round(sum(s for s, _ in rows) / n, 1) if n else None,
            )
        )
    return out


def build_factor_frequencies(
    outcomes: list[PursuitOutcome], limit: int = 10
) -> list[FactorFrequency]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    display: dict[str, str] = {}
    for po in outcomes:
        for factor in po.outcome_factors or []:
            key = normalize_key(factor)
            if not key:
                continue
            display.setdefault(key, factor)
            if po.outcome == "won":
                counts[key][0] += 1
            elif po.outcome == "lost":
                counts[key][1] += 1
    rows = [
        FactorFrequency(factor=display[k], in_wins=w, in_losses=loss)
        for k, (w, loss) in counts.items()
        if w or loss
    ]
    rows.sort(key=lambda f: -(f.in_wins + f.in_losses))
    return rows[:limit]


# ── DB: outcome capture + side effects ─────────────────────────────────────


async def get_outcome(
    db: AsyncSession, *, opportunity_id: uuid.UUID
) -> PursuitOutcome | None:
    return (
        await db.execute(
            select(PursuitOutcome)
            .where(PursuitOutcome.opportunity_id == opportunity_id)
            .options(selectinload(PursuitOutcome.recommendation_outcomes))
        )
    ).scalar_one_or_none()


async def record_outcome(
    db: AsyncSession,
    *,
    opportunity: Opportunity,
    payload: OutcomeRecordRequest,
    user_id: uuid.UUID | None,
) -> PursuitOutcome:
    """Record (or revise) a pursuit outcome and run the learning loop."""
    existing = await get_outcome(db, opportunity_id=opportunity.id)
    is_update = existing is not None
    po = existing or PursuitOutcome(
        workspace_id=opportunity.workspace_id, opportunity_id=opportunity.id
    )
    po.outcome = payload.outcome
    po.decided_at = payload.decided_at
    po.awarded_value_cents = payload.awarded_value_cents
    po.awarded_to_competitor = payload.awarded_to_competitor
    po.outcome_factors = payload.outcome_factors or None
    po.debrief_notes = payload.debrief_notes
    po.recorded_by_user_id = user_id
    db.add(po)

    # Lifecycle: outcome capture is the terminal stage transition.
    stage = OUTCOME_TO_STAGE.get(payload.outcome)
    if stage and opportunity.capture_stage != stage:
        opportunity.capture_stage = stage
        db.add(opportunity)
    await db.flush()

    await _snapshot_recommendations(db, outcome=po)
    await recompute_graph_outcomes(db, workspace_id=opportunity.workspace_id)
    from app.services.proposal_repository_service import sync_asset_outcomes_from_opportunity

    await sync_asset_outcomes_from_opportunity(db, opportunity_id=opportunity.id)

    await write_audit(
        db,
        action="outcome.updated" if is_update else "outcome.recorded",
        workspace_id=opportunity.workspace_id,
        actor_user_id=user_id,
        target_type="opportunity",
        target_id=opportunity.id,
        meta={"outcome": payload.outcome},
    )
    await db.flush()
    return await get_outcome(db, opportunity_id=opportunity.id)  # type: ignore[return-value]


async def delete_outcome(
    db: AsyncSession,
    *,
    opportunity: Opportunity,
    user_id: uuid.UUID | None,
) -> bool:
    existing = await get_outcome(db, opportunity_id=opportunity.id)
    if existing is None:
        return False
    await db.delete(existing)
    await db.flush()
    await recompute_graph_outcomes(db, workspace_id=opportunity.workspace_id)
    from app.services.proposal_repository_service import sync_asset_outcomes_from_opportunity

    await sync_asset_outcomes_from_opportunity(db, opportunity_id=opportunity.id)
    await write_audit(
        db,
        action="outcome.deleted",
        workspace_id=opportunity.workspace_id,
        actor_user_id=user_id,
        target_type="opportunity",
        target_id=opportunity.id,
        meta={"outcome": existing.outcome},
    )
    return True


async def _snapshot_recommendations(
    db: AsyncSession, *, outcome: PursuitOutcome
) -> None:
    """Replace recommendation snapshots from the latest ok output per module."""
    for ro in list(
        (
            await db.execute(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.pursuit_outcome_id == outcome.id
                )
            )
        )
        .scalars()
        .all()
    ):
        await db.delete(ro)

    rows = (
        await db.execute(
            select(AIOutput)
            .where(
                AIOutput.opportunity_id == outcome.opportunity_id,
                AIOutput.module_id.in_(list(RECOMMENDATION_SOURCES)),
                AIOutput.status == "ok",
            )
            .order_by(AIOutput.created_at.desc())
        )
    ).scalars()
    latest_by_module: dict[str, AIOutput] = {}
    for row in rows:
        latest_by_module.setdefault(row.module_id, row)

    for module_id, ai in latest_by_module.items():
        snap = extract_recommendation(module_id, ai.output_json or {})
        if snap is None:
            continue
        db.add(
            RecommendationOutcome(
                workspace_id=outcome.workspace_id,
                opportunity_id=outcome.opportunity_id,
                pursuit_outcome_id=outcome.id,
                ai_output_id=ai.id,
                module_id=module_id,
                recommendation_type=snap.recommendation_type,
                predicted_label=snap.predicted_label,
                predicted_score=snap.predicted_score,
                aligned=compute_alignment(
                    snap.recommendation_type,
                    snap.predicted_label,
                    snap.predicted_score,
                    outcome.outcome,
                ),
            )
        )
    await db.flush()


async def recompute_graph_outcomes(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> int:
    """Recompute wins / losses / win_rate / outcome_weight for every entity.

    Full idempotent rescan: reset to the "no signal" state, then apply stats
    from currently recorded decided outcomes.
    """
    await db.execute(
        update(GraphEntity)
        .where(GraphEntity.workspace_id == workspace_id)
        .values(wins=0, losses=0, win_rate=None, outcome_weight=1.0)
    )
    outcome_by_opp = {
        po.opportunity_id: po.outcome
        for po in (
            await db.execute(
                select(PursuitOutcome).where(
                    PursuitOutcome.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    }
    if not outcome_by_opp:
        return 0
    edges = await graph_service.workspace_edges(db, workspace_id=workspace_id)
    records = compute_entity_outcome_records(edges, outcome_by_opp)
    updated = 0
    for entity_id, opp_outcomes in records.items():
        wins = sum(1 for o in opp_outcomes.values() if o == "won")
        losses = sum(1 for o in opp_outcomes.values() if o == "lost")
        await db.execute(
            update(GraphEntity)
            .where(GraphEntity.id == entity_id)
            .values(
                wins=wins,
                losses=losses,
                win_rate=compute_win_rate(wins, losses),
                outcome_weight=laplace_weight(wins, losses),
            )
        )
        updated += 1
    await db.flush()
    return updated


# ── DB: workspace analysis ─────────────────────────────────────────────────


async def list_outcomes(
    db: AsyncSession, *, workspace_id: uuid.UUID, outcome: str | None = None
) -> list[tuple[PursuitOutcome, Opportunity]]:
    stmt = (
        select(PursuitOutcome, Opportunity)
        .join(Opportunity, Opportunity.id == PursuitOutcome.opportunity_id)
        .where(PursuitOutcome.workspace_id == workspace_id)
        .options(selectinload(PursuitOutcome.recommendation_outcomes))
        .order_by(PursuitOutcome.updated_at.desc())
    )
    if outcome:
        stmt = stmt.where(PursuitOutcome.outcome == outcome)
    return [(po, opp) for po, opp in (await db.execute(stmt)).all()]


def _pattern_for_entity(
    ent: GraphEntity,
    opp_outcomes: dict[uuid.UUID, str],
    opps: dict[uuid.UUID, Opportunity],
    *,
    awards_taken: int | None = None,
    decided_value_cents: int | None = None,
) -> OutcomePattern:
    wins = sum(1 for o in opp_outcomes.values() if o == "won")
    losses = sum(1 for o in opp_outcomes.values() if o == "lost")
    sources = sorted(
        (
            SourcePursuit(id=oid, name=opps[oid].name, outcome=outc)
            for oid, outc in opp_outcomes.items()
            if oid in opps
        ),
        key=lambda s: s.name,
    )
    return OutcomePattern(
        label=ent.name,
        entity_type=ent.entity_type,
        wins=wins,
        losses=losses,
        win_rate=compute_win_rate(wins, losses),
        outcome_weight=laplace_weight(wins, losses),
        observation=observation_text(ent.name, wins, losses),
        awards_taken=awards_taken,
        decided_value_cents=decided_value_cents,
        source_pursuits=sources,
    )


_WIN_PATTERN_TYPES = ("win_theme", "discriminator", "capability", "technology")
_LOSS_PATTERN_TYPES = _WIN_PATTERN_TYPES + ("risk",)


async def build_report(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> OutcomeIntelligenceReport:
    outcomes = list(
        (
            await db.execute(
                select(PursuitOutcome)
                .where(PursuitOutcome.workspace_id == workspace_id)
                .options(selectinload(PursuitOutcome.recommendation_outcomes))
            )
        )
        .scalars()
        .all()
    )
    opps = {
        o.id: o
        for o in (
            await db.execute(
                select(Opportunity).where(Opportunity.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    }
    edges = await graph_service.workspace_edges(db, workspace_id=workspace_id)
    entity_ids = {e.source_entity_id for e in edges} | {
        e.target_entity_id for e in edges
    }
    entities = await graph_service.entities_by_id(db, list(entity_ids))

    outcome_by_opp = {po.opportunity_id: po.outcome for po in outcomes}
    records = compute_entity_outcome_records(edges, outcome_by_opp)

    wins = sum(1 for po in outcomes if po.outcome == "won")
    losses = sum(1 for po in outcomes if po.outcome == "lost")
    no_bids = sum(1 for po in outcomes if po.outcome == "no_bid")
    value_won = sum(
        po.awarded_value_cents or 0 for po in outcomes if po.outcome == "won"
    )

    rec_rows = [ro for po in outcomes for ro in po.recommendation_outcomes]
    assessed = [ro for ro in rec_rows if ro.aligned is not None]
    alignment_rate = (
        round(sum(1 for ro in assessed if ro.aligned) / len(assessed), 3)
        if assessed
        else None
    )

    summary = OutcomeSummary(
        recorded=len(outcomes),
        decided=wins + losses,
        wins=wins,
        losses=losses,
        win_rate=compute_win_rate(wins, losses),
        no_bids=no_bids,
        value_won_cents=value_won,
        recommendation_alignment_rate=alignment_rate,
    )

    # ── Patterns and trends ────────────────────────────────────────────────
    def _patterns(types: tuple[str, ...]) -> list[OutcomePattern]:
        out = []
        for eid, opp_outcomes in records.items():
            ent = entities.get(eid)
            if ent is None or ent.entity_type not in types:
                continue
            out.append(_pattern_for_entity(ent, opp_outcomes, opps))
        return out

    candidates = _patterns(_LOSS_PATTERN_TYPES)
    win_patterns = sorted(
        (p for p in candidates if p.wins > 0 and p.entity_type in _WIN_PATTERN_TYPES),
        key=lambda p: (-p.outcome_weight, -p.wins, p.label.lower()),
    )[:10]
    loss_patterns = sorted(
        (p for p in candidates if p.losses > 0),
        key=lambda p: (-p.losses, p.outcome_weight, p.label.lower()),
    )[:10]

    agency_trends: list[OutcomePattern] = []
    for eid, opp_outcomes in records.items():
        ent = entities.get(eid)
        if ent is None or ent.entity_type != "agency":
            continue
        value = sum(
            po.awarded_value_cents or 0
            for po in outcomes
            if po.outcome == "won" and po.opportunity_id in opp_outcomes
        )
        agency_trends.append(
            _pattern_for_entity(ent, opp_outcomes, opps, decided_value_cents=value)
        )
    agency_trends.sort(key=lambda p: (-(p.wins + p.losses), p.label.lower()))

    capability_trends = sorted(
        _patterns(("capability",)),
        key=lambda p: (-(p.wins + p.losses), -p.outcome_weight, p.label.lower()),
    )[:12]

    competitor_trends: list[OutcomePattern] = []
    awards_by_competitor: dict[str, int] = defaultdict(int)
    for po in outcomes:
        if po.outcome == "lost" and po.awarded_to_competitor:
            awards_by_competitor[normalize_key(po.awarded_to_competitor)] += 1
    for eid, opp_outcomes in records.items():
        ent = entities.get(eid)
        if ent is None or ent.entity_type != "competitor":
            continue
        competitor_trends.append(
            _pattern_for_entity(
                ent,
                opp_outcomes,
                opps,
                awards_taken=awards_by_competitor.get(ent.normalized_key, 0),
            )
        )
    competitor_trends.sort(
        key=lambda p: (-(p.awards_taken or 0), -(p.wins + p.losses), p.label.lower())
    )

    # ── Recommendation performance ─────────────────────────────────────────
    perf: list[RecommendationPerformance] = []
    by_type: dict[tuple[str, str], list[RecommendationOutcome]] = defaultdict(list)
    for ro in rec_rows:
        by_type[(ro.recommendation_type, ro.module_id)].append(ro)
    for (rec_type, module_id), rows in sorted(by_type.items()):
        assessed_rows = [r for r in rows if r.aligned is not None]
        aligned_n = sum(1 for r in assessed_rows if r.aligned)
        perf.append(
            RecommendationPerformance(
                recommendation_type=rec_type,
                module_id=module_id,
                total=len(assessed_rows),
                aligned=aligned_n,
                alignment_rate=(
                    round(aligned_n / len(assessed_rows), 3) if assessed_rows else None
                ),
            )
        )

    scored = [
        (ro.predicted_score, outcome_by_opp.get(ro.opportunity_id, ""))
        for ro in rec_rows
        if ro.recommendation_type == "win_confidence" and ro.predicted_score is not None
    ]
    calibration = build_calibration([(s, o) for s, o in scored if o])

    observations = build_strategic_observations(
        summary=summary,
        win_patterns=win_patterns,
        loss_patterns=loss_patterns,
        agency_trends=agency_trends,
        competitor_trends=competitor_trends,
        factor_frequencies=build_factor_frequencies(outcomes),
        performance=perf,
    )

    return OutcomeIntelligenceReport(
        summary=summary,
        win_patterns=win_patterns,
        loss_patterns=loss_patterns,
        factor_frequencies=build_factor_frequencies(outcomes),
        agency_trends=agency_trends,
        capability_trends=capability_trends,
        competitor_trends=competitor_trends,
        recommendation_performance=perf,
        calibration=calibration,
        strategic_observations=observations,
    )


def build_strategic_observations(
    *,
    summary: OutcomeSummary,
    win_patterns: list[OutcomePattern],
    loss_patterns: list[OutcomePattern],
    agency_trends: list[OutcomePattern],
    competitor_trends: list[OutcomePattern],
    factor_frequencies: list[FactorFrequency],
    performance: list[RecommendationPerformance],
) -> list[StrategicObservation]:
    """Deterministic, evidence-cited observations. Descriptive only — each
    line states what was observed, never why it happened."""
    out: list[StrategicObservation] = []

    if summary.decided:
        rate = round((summary.win_rate or 0) * 100)
        out.append(
            StrategicObservation(
                observation=(
                    f"{summary.decided} decided pursuit(s) recorded: {summary.wins} won, "
                    f"{summary.losses} lost ({rate}% historical win rate)."
                ),
                kind="observed_pattern",
                sources=[f"{summary.recorded} recorded outcome(s)"],
            )
        )
    strongest = next((p for p in win_patterns if p.wins >= 2), None)
    if strongest:
        out.append(
            StrategicObservation(
                observation=(
                    f"Observed pattern: {strongest.entity_type.replace('_', ' ')} "
                    f"'{strongest.label}' appeared in {strongest.wins} won pursuit(s) "
                    f"and {strongest.losses} lost."
                ),
                kind="observed_pattern",
                sources=[s.name for s in strongest.source_pursuits],
            )
        )
    recurring_loss = next((p for p in loss_patterns if p.losses >= 2), None)
    if recurring_loss:
        out.append(
            StrategicObservation(
                observation=(
                    f"Historical correlation: {recurring_loss.entity_type.replace('_', ' ')} "
                    f"'{recurring_loss.label}' appeared in {recurring_loss.losses} lost "
                    f"pursuit(s) and {recurring_loss.wins} won."
                ),
                kind="historical_correlation",
                sources=[s.name for s in recurring_loss.source_pursuits],
            )
        )
    top_factor = next(
        (f for f in factor_frequencies if f.in_losses >= 2 and f.in_losses > f.in_wins),
        None,
    )
    if top_factor:
        out.append(
            StrategicObservation(
                observation=(
                    f"Historical correlation: debrief factor '{top_factor.factor}' was "
                    f"cited in {top_factor.in_losses} lost pursuit(s)."
                ),
                kind="historical_correlation",
                sources=["Recorded debrief factors"],
            )
        )
    busiest_agency = next((a for a in agency_trends if a.wins + a.losses >= 2), None)
    if busiest_agency:
        out.append(
            StrategicObservation(
                observation=(
                    f"Agency trend: {busiest_agency.wins} won and {busiest_agency.losses} "
                    f"lost pursuit(s) recorded at {busiest_agency.label}."
                ),
                kind="observed_pattern",
                sources=[s.name for s in busiest_agency.source_pursuits],
            )
        )
    top_competitor = next(
        (c for c in competitor_trends if (c.awards_taken or 0) >= 1), None
    )
    if top_competitor:
        out.append(
            StrategicObservation(
                observation=(
                    f"Competitor trend: '{top_competitor.label}' took the award in "
                    f"{top_competitor.awards_taken} recorded loss(es)."
                ),
                kind="observed_pattern",
                sources=[s.name for s in top_competitor.source_pursuits],
            )
        )
    assessed_perf = [p for p in performance if p.total]
    if assessed_perf:
        total = sum(p.total for p in assessed_perf)
        aligned = sum(p.aligned for p in assessed_perf)
        out.append(
            StrategicObservation(
                observation=(
                    f"Recommendation performance: MissionIQ recommendations aligned with "
                    f"recorded outcomes in {aligned} of {total} assessed case(s) — a "
                    "historical correlation, not a causal accuracy measure."
                ),
                kind="historical_correlation",
                sources=[f"{p.module_id} ({p.aligned}/{p.total})" for p in assessed_perf],
            )
        )
    return out


# ── Module support: compact context for capture.outcome_intelligence ──────


async def workspace_outcome_context(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> dict[str, Any] | None:
    """Compact view of the workspace outcome analysis for prompt consumption.

    Returns None when no outcomes are recorded yet, so the module can flag
    the missing input honestly instead of inventing a track record.
    """
    report = await build_report(db, workspace_id=workspace_id)
    if report.summary.recorded == 0:
        return None

    def _compact(patterns: list[OutcomePattern], n: int = 6) -> list[dict[str, Any]]:
        return [
            {
                "label": p.label,
                "entity_type": p.entity_type,
                "wins": p.wins,
                "losses": p.losses,
                "win_rate": p.win_rate,
                "observation": p.observation,
            }
            for p in patterns[:n]
        ]

    return {
        "summary": report.summary.model_dump(),
        "win_patterns": _compact(report.win_patterns),
        "loss_patterns": _compact(report.loss_patterns),
        "agency_trends": _compact(report.agency_trends, 4),
        "competitor_trends": _compact(report.competitor_trends, 4),
        "loss_factors": [
            {"factor": f.factor, "in_wins": f.in_wins, "in_losses": f.in_losses}
            for f in report.factor_frequencies[:6]
        ],
        "observations": [o.observation for o in report.strategic_observations],
    }
