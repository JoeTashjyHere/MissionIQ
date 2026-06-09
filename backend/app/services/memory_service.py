"""MissionIQ Memory — the reusable intelligence layer over the graph.

Powers four capabilities the rest of the platform consumes:

- **Pursuit Memory** — what we already know relevant to THIS pursuit.
- **Opportunity Similarity Engine** — which prior opportunities resemble it.
- **Historical Insight Repository** — reusable win themes / discriminators /
  risks / competitors across all pursuits.
- **Agency Intelligence Repository** — the accumulated portrait of an agency.

The scoring and aggregation primitives are pure functions (no DB) so they are
directly unit-testable; the async functions wrap them around graph queries.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph import normalize_key
from app.graph import service as graph_service
from app.models import GraphEdge, GraphEntity, Opportunity
from app.schemas.memory import (
    AgencyIntelligence,
    HistoricalInsightRepository,
    MemoryItem,
    PursuitMemory,
    SimilarOpportunity,
    SourceOpportunity,
)

# Relations whose targets are meaningful "signal" entities for similarity.
_SIGNAL_RELATIONS = {
    "opportunity_involves_technology",
    "opportunity_requires_capability",
    "company_has_capability",
    "opportunity_has_competitor",
    "opportunity_has_discriminator",
    "opportunity_has_win_theme",
}

_MEMORY_RELATIONS = {
    "risk": "opportunity_has_risk",
    "discriminator": "opportunity_has_discriminator",
    "win_theme": "opportunity_has_win_theme",
    "competitor": "opportunity_has_competitor",
}


# ── Pure: similarity scoring ──────────────────────────────────────────────


@dataclass
class OppFeatures:
    opportunity_id: uuid.UUID
    name: str
    agency: str | None = None
    sub_agency: str | None = None
    naics_code: str | None = None
    contract_vehicle: str | None = None
    signal_entity_ids: set[uuid.UUID] = field(default_factory=set)

    @property
    def agency_key(self) -> str:
        return normalize_key(self.agency or "")

    @property
    def sub_agency_key(self) -> str:
        return normalize_key(self.sub_agency or "")

    @property
    def vehicle_key(self) -> str:
        return normalize_key(self.contract_vehicle or "")


def score_opportunity_similarity(
    a: OppFeatures, b: OppFeatures
) -> tuple[float, list[str], int]:
    """Return (score 0–1, human reasons, shared signal-entity count)."""
    score = 0.0
    reasons: list[str] = []

    if a.agency_key and a.agency_key == b.agency_key:
        score += 0.35
        reasons.append(f"Same agency: {b.agency}")
    if a.sub_agency_key and a.sub_agency_key == b.sub_agency_key:
        score += 0.10
        reasons.append(f"Same sub-agency: {b.sub_agency}")
    if a.naics_code and a.naics_code == b.naics_code:
        score += 0.20
        reasons.append(f"Same NAICS: {b.naics_code}")
    if a.vehicle_key and a.vehicle_key == b.vehicle_key:
        score += 0.15
        reasons.append(f"Same contract vehicle: {b.contract_vehicle}")

    shared = a.signal_entity_ids & b.signal_entity_ids
    shared_n = len(shared)
    union = a.signal_entity_ids | b.signal_entity_ids
    if union:
        jaccard = shared_n / len(union)
        score += 0.20 * jaccard
        if shared_n:
            reasons.append(
                f"{shared_n} shared technology/capability/competitor signal(s)"
            )

    return min(score, 1.0), reasons, shared_n


# ── Pure: memory item aggregation ─────────────────────────────────────────


@dataclass
class ItemOccurrence:
    label: str
    entity_type: str
    opportunity_id: uuid.UUID
    opportunity_name: str
    attributes: dict = field(default_factory=dict)


@dataclass
class AggregatedItem:
    label: str
    entity_type: str
    basis: str  # "historical" | "current"
    frequency: int
    sources: list[tuple[uuid.UUID, str]]
    attributes: dict


def aggregate_memory_items(
    occurrences: list[ItemOccurrence],
    *,
    current_opportunity_id: uuid.UUID,
) -> list[AggregatedItem]:
    """Group occurrences by normalized label and classify each item's basis.

    An item observed on any opportunity OTHER than the current one is
    ``historical`` (reusable institutional knowledge). An item seen only on
    the current opportunity is ``current``.
    """
    grouped: dict[str, list[ItemOccurrence]] = {}
    for occ in occurrences:
        grouped.setdefault(normalize_key(occ.label), []).append(occ)

    items: list[AggregatedItem] = []
    for occs in grouped.values():
        opp_ids = {o.opportunity_id for o in occs}
        prior_ids = opp_ids - {current_opportunity_id}
        basis = "historical" if prior_ids else "current"
        # Prefer a prior occurrence's label/attrs for display when historical.
        display = next(
            (o for o in occs if o.opportunity_id != current_opportunity_id), occs[0]
        )
        sources = sorted(
            {(o.opportunity_id, o.opportunity_name) for o in occs},
            key=lambda s: s[1],
        )
        items.append(
            AggregatedItem(
                label=display.label,
                entity_type=display.entity_type,
                basis=basis,
                frequency=len(prior_ids) if prior_ids else len(opp_ids),
                sources=sources,
                attributes=display.attributes,
            )
        )

    items.sort(key=lambda i: (i.basis != "historical", -i.frequency, i.label.lower()))
    return items


def _to_memory_item(agg: AggregatedItem) -> MemoryItem:
    return MemoryItem(
        label=agg.label,
        basis=agg.basis,  # type: ignore[arg-type]
        entity_type=agg.entity_type,
        frequency=agg.frequency,
        source_opportunities=[
            SourceOpportunity(id=oid, name=name) for oid, name in agg.sources
        ],
        attributes=agg.attributes or {},
    )


# ── DB-backed assembly ────────────────────────────────────────────────────


async def _load_graph(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> tuple[list[GraphEdge], dict[uuid.UUID, GraphEntity], dict[uuid.UUID, Opportunity]]:
    edges = await graph_service.workspace_edges(db, workspace_id=workspace_id)
    entity_ids = {e.source_entity_id for e in edges} | {e.target_entity_id for e in edges}
    entities = await graph_service.entities_by_id(db, list(entity_ids))
    opps = list(
        (
            await db.execute(
                select(Opportunity).where(Opportunity.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    return edges, entities, {o.id: o for o in opps}


def _build_features(
    edges: list[GraphEdge], opps: dict[uuid.UUID, Opportunity]
) -> dict[uuid.UUID, OppFeatures]:
    feats: dict[uuid.UUID, OppFeatures] = {}
    for oid, opp in opps.items():
        feats[oid] = OppFeatures(
            opportunity_id=oid,
            name=opp.name,
            agency=opp.agency,
            sub_agency=opp.sub_agency,
            naics_code=opp.naics_code,
            contract_vehicle=opp.contract_vehicle,
        )
    for e in edges:
        if e.opportunity_id in feats and e.relation in _SIGNAL_RELATIONS:
            feats[e.opportunity_id].signal_entity_ids.add(e.target_entity_id)
    return feats


def _occurrences_for_relation(
    edges: list[GraphEdge],
    entities: dict[uuid.UUID, GraphEntity],
    opps: dict[uuid.UUID, Opportunity],
    relation: str,
    *,
    restrict_opps: set[uuid.UUID] | None = None,
) -> list[ItemOccurrence]:
    out: list[ItemOccurrence] = []
    for e in edges:
        if e.relation != relation or e.opportunity_id is None:
            continue
        if restrict_opps is not None and e.opportunity_id not in restrict_opps:
            continue
        ent = entities.get(e.target_entity_id)
        opp = opps.get(e.opportunity_id)
        if ent is None or opp is None:
            continue
        out.append(
            ItemOccurrence(
                label=ent.name,
                entity_type=ent.entity_type,
                opportunity_id=e.opportunity_id,
                opportunity_name=opp.name,
                attributes=e.attributes or ent.attributes or {},
            )
        )
    return out


async def find_similar_opportunities(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    threshold: float = 0.15,
    limit: int = 5,
) -> list[SimilarOpportunity]:
    edges, _entities, opps = await _load_graph(db, workspace_id=workspace_id)
    feats = _build_features(edges, opps)
    target = feats.get(opportunity_id)
    if target is None:
        return []
    scored: list[SimilarOpportunity] = []
    for oid, other in feats.items():
        if oid == opportunity_id:
            continue
        score, reasons, shared = score_opportunity_similarity(target, other)
        if score >= threshold:
            scored.append(
                SimilarOpportunity(
                    opportunity_id=oid,
                    name=other.name,
                    agency=other.agency,
                    score=round(score, 3),
                    reasons=reasons,
                    shared_entities=shared,
                )
            )
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:limit]


async def build_pursuit_memory(
    db: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> PursuitMemory:
    edges, entities, opps = await _load_graph(db, workspace_id=workspace_id)
    current = opps.get(opportunity_id)
    if current is None:
        raise ValueError("opportunity not found")

    feats = _build_features(edges, opps)
    target = feats.get(opportunity_id)

    similar: list[SimilarOpportunity] = []
    if target is not None:
        for oid, other in feats.items():
            if oid == opportunity_id:
                continue
            score, reasons, shared = score_opportunity_similarity(target, other)
            if score >= 0.15:
                similar.append(
                    SimilarOpportunity(
                        opportunity_id=oid,
                        name=other.name,
                        agency=other.agency,
                        score=round(score, 3),
                        reasons=reasons,
                        shared_entities=shared,
                    )
                )
        similar.sort(key=lambda s: s.score, reverse=True)
        similar = similar[:5]

    # Relevant prior opportunities: similar ∪ same-agency, else all others.
    agency_key = normalize_key(current.agency or "")
    same_agency_ids = {
        oid
        for oid, o in opps.items()
        if oid != opportunity_id and normalize_key(o.agency or "") == agency_key and agency_key
    }
    relevant = {s.opportunity_id for s in similar} | same_agency_ids
    all_other = {oid for oid in opps if oid != opportunity_id}
    scope = relevant or all_other

    def _items(relation: str, include_current: bool = True) -> list[MemoryItem]:
        restrict = scope | ({opportunity_id} if include_current else set())
        occ = _occurrences_for_relation(
            edges, entities, opps, relation, restrict_opps=restrict
        )
        aggs = aggregate_memory_items(occ, current_opportunity_id=opportunity_id)
        # Surface historical items first; cap for a tight executive view.
        return [_to_memory_item(a) for a in aggs][:8]

    prior_risks = _items("opportunity_has_risk")
    prior_discriminators = _items("opportunity_has_discriminator")
    prior_win_themes = _items("opportunity_has_win_theme")

    agency_intel = await _agency_intelligence(
        edges, entities, opps, agency=current.agency, exclude_opp=None
    )

    inferences = _build_inferences(
        similar=similar,
        prior_risks=prior_risks,
        prior_win_themes=prior_win_themes,
        agency=current.agency,
    )

    has_history = bool(all_other)
    summary = _build_summary(
        has_history=has_history,
        similar=similar,
        prior_risks=prior_risks,
        prior_win_themes=prior_win_themes,
        agency=current.agency,
    )

    return PursuitMemory(
        opportunity_id=opportunity_id,
        opportunity_name=current.name,
        has_history=has_history,
        summary=summary,
        similar_opportunities=similar,
        prior_risks=prior_risks,
        prior_discriminators=prior_discriminators,
        prior_win_themes=prior_win_themes,
        agency_intelligence=agency_intel,
        inferences=inferences,
        graph_stats=await graph_service.graph_stats(db, workspace_id=workspace_id),
    )


def _build_inferences(
    *,
    similar: list[SimilarOpportunity],
    prior_risks: list[MemoryItem],
    prior_win_themes: list[MemoryItem],
    agency: str | None,
) -> list[str]:
    out: list[str] = []
    recurring_risks = [r for r in prior_risks if r.basis == "historical" and r.frequency >= 2]
    if recurring_risks:
        out.append(
            f"'{recurring_risks[0].label}' has recurred on {recurring_risks[0].frequency} "
            "prior pursuits — treat it as a standing risk and pre-empt it in capture."
        )
    recurring_themes = [
        t for t in prior_win_themes if t.basis == "historical" and t.frequency >= 2
    ]
    if recurring_themes:
        scope = f"{agency} " if agency else ""
        out.append(
            f"Win theme '{recurring_themes[0].label}' has resonated across "
            f"{recurring_themes[0].frequency} {scope}pursuits — a strong candidate to lead with."
        )
    if similar:
        out.append(
            f"{len(similar)} similar prior opportunit{'y' if len(similar) == 1 else 'ies'} "
            "found — reuse their discriminators and proven risk mitigations rather than starting cold."
        )
    return out


def _build_summary(
    *,
    has_history: bool,
    similar: list[SimilarOpportunity],
    prior_risks: list[MemoryItem],
    prior_win_themes: list[MemoryItem],
    agency: str | None,
) -> str:
    if not has_history:
        return (
            "No prior pursuit history yet. As you analyze opportunities, MissionIQ "
            "builds institutional memory — similar opportunities, recurring risks, "
            "and proven win themes will surface here automatically."
        )
    bits = []
    if similar:
        bits.append(f"{len(similar)} similar prior pursuit(s)")
    n_hist_risks = len([r for r in prior_risks if r.basis == "historical"])
    if n_hist_risks:
        bits.append(f"{n_hist_risks} prior risk(s) to revisit")
    n_hist_themes = len([t for t in prior_win_themes if t.basis == "historical"])
    if n_hist_themes:
        bits.append(f"{n_hist_themes} reusable win theme(s)")
    body = ", ".join(bits) if bits else "related institutional knowledge"
    scope = f" for {agency}" if agency else ""
    return f"MissionIQ recalled {body}{scope} from prior pursuits."


async def _agency_intelligence(
    edges: list[GraphEdge],
    entities: dict[uuid.UUID, GraphEntity],
    opps: dict[uuid.UUID, Opportunity],
    *,
    agency: str | None,
    exclude_opp: uuid.UUID | None,
) -> AgencyIntelligence | None:
    if not agency:
        return None
    agency_key = normalize_key(agency)
    agency_opp_ids = {
        oid
        for oid, o in opps.items()
        if normalize_key(o.agency or "") == agency_key and oid != exclude_opp
    }
    # Agency node attributes (mission/goals enriched by Customer DNA).
    agency_entity = next(
        (
            e
            for e in entities.values()
            if e.entity_type == "agency" and e.normalized_key == agency_key
        ),
        None,
    )
    mission = (agency_entity.attributes or {}).get("mission") if agency_entity else None
    goals = (agency_entity.attributes or {}).get("strategic_goals") if agency_entity else None

    def _agg(relation: str) -> list[MemoryItem]:
        occ = _occurrences_for_relation(
            edges, entities, opps, relation, restrict_opps=agency_opp_ids
        )
        # For the agency repository, every item is institutional/historical.
        aggs = aggregate_memory_items(
            occ, current_opportunity_id=uuid.UUID(int=0)
        )
        return [_to_memory_item(a) for a in aggs][:6]

    return AgencyIntelligence(
        agency=agency,
        mission=mission,
        strategic_goals=goals if isinstance(goals, list) else [],
        opportunities_count=len(agency_opp_ids),
        recurring_risks=_agg("opportunity_has_risk"),
        recurring_win_themes=_agg("opportunity_has_win_theme"),
        known_competitors=_agg("opportunity_has_competitor"),
    )


async def historical_insights(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> HistoricalInsightRepository:
    edges, entities, opps = await _load_graph(db, workspace_id=workspace_id)
    sentinel = uuid.UUID(int=0)  # nothing is "current" in the global repository

    def _agg(relation: str, limit: int = 12) -> list[MemoryItem]:
        occ = _occurrences_for_relation(edges, entities, opps, relation)
        aggs = aggregate_memory_items(occ, current_opportunity_id=sentinel)
        return [_to_memory_item(a) for a in aggs][:limit]

    return HistoricalInsightRepository(
        win_themes=_agg("opportunity_has_win_theme"),
        discriminators=_agg("opportunity_has_discriminator"),
        risks=_agg("opportunity_has_risk"),
        competitors=_agg("opportunity_has_competitor"),
        graph_stats=await graph_service.graph_stats(db, workspace_id=workspace_id),
    )
