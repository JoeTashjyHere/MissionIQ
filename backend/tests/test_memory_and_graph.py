"""Unit tests for the Memory + Knowledge Graph layer (pure functions, no DB)."""
from __future__ import annotations

import uuid

from app.graph.extract import (
    extract_facts,
    extract_opportunity_base,
    normalize_key,
)
from app.services.memory_service import (
    ItemOccurrence,
    OppFeatures,
    aggregate_memory_items,
    score_opportunity_similarity,
)

_OPP = {
    "name": "DHS Cyber Operations",
    "agency": "Department of Homeland Security",
    "sub_agency": "CISA",
    "contract_vehicle": "GSA OASIS+",
    "incumbent": "Acme Defense",
    "naics_code": "541512",
    "capture_stage": "capture",
}


# ── normalize_key ──────────────────────────────────────────────────────────


def test_normalize_key_dedupes_variants():
    assert normalize_key("  Acme  Defense, Inc. ") == "acme defense inc"
    assert normalize_key("Acme Defense Inc") == "acme defense inc"


# ── extraction ─────────────────────────────────────────────────────────────


def test_opportunity_base_extracts_agency_vehicle_incumbent():
    bundle = extract_opportunity_base(_OPP)
    rels = {e.relation for e in bundle.edges}
    assert "opportunity_for_agency" in rels
    assert "opportunity_uses_vehicle" in rels
    assert "opportunity_has_incumbent" in rels
    # The incumbent is modeled as a competitor entity.
    incumbent = next(e for e in bundle.edges if e.relation == "opportunity_has_incumbent")
    assert incumbent.target.entity_type == "competitor"
    assert incumbent.target.name == "Acme Defense"


def test_risk_register_facts_become_risk_entities():
    output = {
        "capture_risks": [
            {"title": "Aggressive transition timeline", "severity": "high"},
        ],
        "proposal_risks": [{"title": "Thin past performance", "severity": "medium"}],
    }
    bundle = extract_facts("capture.risk_register", output, _OPP)
    risks = [e for e in bundle.edges if e.relation == "opportunity_has_risk"]
    assert {e.target.name for e in risks} == {
        "Aggressive transition timeline",
        "Thin past performance",
    }
    assert all(e.target.entity_type == "risk" for e in risks)
    assert risks[0].attributes.get("lane") == "capture"


def test_capability_match_facts_split_into_themes_and_discriminators():
    output = {
        "reusable_win_themes": ["Zero-downtime transition"],
        "suggested_discriminators": ["Cleared 24x7 SOC bench"],
        "missing_capabilities": ["FedRAMP High ATO"],
    }
    bundle = extract_facts("capture.capability_match", output, _OPP)
    by_rel = {}
    for e in bundle.edges:
        by_rel.setdefault(e.relation, []).append(e.target.name)
    assert by_rel["opportunity_has_win_theme"] == ["Zero-downtime transition"]
    assert by_rel["opportunity_has_discriminator"] == ["Cleared 24x7 SOC bench"]
    assert by_rel["opportunity_requires_capability"] == ["FedRAMP High ATO"]


def test_win_strategy_facts_handle_strategic_point_objects():
    output = {
        "win_themes": [{"statement": "Mission-first delivery", "basis": "evidence"}],
        "key_discriminators": [{"statement": "Surge-ready cleared staff"}],
        "competitive_assessment": {
            "competitors": [{"name": "Globex Corp", "threat_level": "high"}]
        },
    }
    bundle = extract_facts("capture.win_strategy", output, _OPP)
    names = {(e.relation, e.target.name) for e in bundle.edges}
    assert ("opportunity_has_win_theme", "Mission-first delivery") in names
    assert ("opportunity_has_discriminator", "Surge-ready cleared staff") in names
    assert ("opportunity_has_competitor", "Globex Corp") in names


def test_customer_dna_enriches_agency_entity():
    output = {
        "mission": "Secure the homeland",
        "strategic_goals": ["Zero trust", "Resilience"],
        "technology_priorities": ["Zero Trust", "Cloud"],
    }
    bundle = extract_facts("capture.customer_dna", output, _OPP)
    agency = next(e for e in bundle.entities if e.entity_type == "agency")
    assert agency.attributes["mission"] == "Secure the homeland"
    techs = {e.target.name for e in bundle.edges if e.relation == "opportunity_involves_technology"}
    assert techs == {"Zero Trust", "Cloud"}


def test_unknown_module_contributes_nothing():
    assert extract_facts("capture.unknown", {"foo": "bar"}, _OPP).edges == []


# ── similarity scoring ─────────────────────────────────────────────────────


def _feat(agency, naics=None, vehicle=None, ents=None):
    return OppFeatures(
        opportunity_id=uuid.uuid4(),
        name="x",
        agency=agency,
        naics_code=naics,
        contract_vehicle=vehicle,
        signal_entity_ids=set(ents or []),
    )


def test_same_agency_scores_higher_than_unrelated():
    base = _feat("DHS", naics="541512")
    same = _feat("DHS", naics="541512")
    other = _feat("Department of Energy", naics="237130")
    s_same, reasons, _ = score_opportunity_similarity(base, same)
    s_other, _, _ = score_opportunity_similarity(base, other)
    assert s_same > s_other
    assert any("Same agency" in r for r in reasons)


def test_shared_signal_entities_increase_score_and_count():
    e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    base = _feat("DHS", ents=[e1, e2])
    overlap = _feat("DHS", ents=[e1, e2, e3])
    none = _feat("DHS", ents=[uuid.uuid4()])
    s_overlap, _, shared = score_opportunity_similarity(base, overlap)
    s_none, _, shared_none = score_opportunity_similarity(base, none)
    assert shared == 2
    assert shared_none == 0
    assert s_overlap > s_none


# ── memory item aggregation (basis classification) ─────────────────────────


def test_aggregate_classifies_historical_vs_current():
    current = uuid.uuid4()
    prior_a = uuid.uuid4()
    prior_b = uuid.uuid4()
    occ = [
        # A risk seen on two prior pursuits and the current one → historical.
        ItemOccurrence("Transition risk", "risk", prior_a, "Opp A"),
        ItemOccurrence("Transition risk", "risk", prior_b, "Opp B"),
        ItemOccurrence("Transition risk", "risk", current, "Current"),
        # A risk unique to the current pursuit → current.
        ItemOccurrence("Net-new risk", "risk", current, "Current"),
    ]
    items = {i.label: i for i in aggregate_memory_items(occ, current_opportunity_id=current)}
    assert items["Transition risk"].basis == "historical"
    # Frequency counts distinct PRIOR pursuits when historical.
    assert items["Transition risk"].frequency == 2
    assert items["Net-new risk"].basis == "current"
    # Historical items sort ahead of current ones.
    ordered = aggregate_memory_items(occ, current_opportunity_id=current)
    assert ordered[0].basis == "historical"
