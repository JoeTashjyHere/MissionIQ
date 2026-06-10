"""Proposal asset → knowledge graph mapping."""
from __future__ import annotations

from app.services.proposal_graph import build_graph_bundle, graph_entity_type


def test_graph_entity_type_mapping():
    assert graph_entity_type("executive_summary") == "executive_summary"
    assert graph_entity_type("staffing_approach") == "staffing_narrative"
    assert graph_entity_type("transition_approach") == "transition_narrative"
    assert graph_entity_type("risk_mitigation") == "risk_mitigation"
    assert graph_entity_type("technical_approach") == "proposal_asset"


def test_build_graph_bundle_includes_agency_edge():
    bundle = build_graph_bundle(
        asset_title="Phased transition",
        asset_type="transition_approach",
        agency="CMS",
        opportunity={"name": "CMS Ops", "agency": "CMS"},
        win_themes=["Mission continuity"],
    )
    relations = {e.relation for e in bundle.edges}
    assert "agency_uses_proposal_asset" in relations
    assert "proposal_asset_from_opportunity" in relations
    entity_types = {e.entity_type for e in bundle.entities}
    assert "transition_narrative" in entity_types
    assert "agency" in entity_types
