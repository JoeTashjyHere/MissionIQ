"""Proposal asset vocabulary — models and migration stay aligned."""
from __future__ import annotations

from pathlib import Path

from app.models.graph import ENTITY_TYPES, RELATION_TYPES
from app.models.proposal_asset import ASSET_TYPES, PROPOSAL_DOC_TYPES, USAGE_KINDS


def test_asset_types_cover_repository_libraries():
    assert "executive_summary" in ASSET_TYPES
    assert "win_theme" in ASSET_TYPES
    assert "transition_approach" in ASSET_TYPES
    assert "staffing_approach" in ASSET_TYPES
    assert "past_performance" in ASSET_TYPES


def test_proposal_doc_types_trigger_extraction():
    assert "proposal" in PROPOSAL_DOC_TYPES
    assert "proposal_volume" in PROPOSAL_DOC_TYPES


def test_graph_entity_types_include_proposal_assets():
    for et in (
        "proposal_asset",
        "staffing_narrative",
        "transition_narrative",
        "executive_summary",
        "risk_mitigation",
    ):
        assert et in ENTITY_TYPES


def test_graph_relations_include_proposal_repository():
    for rt in (
        "agency_uses_proposal_asset",
        "proposal_asset_supports_win_theme",
        "proposal_asset_linked_capability",
        "proposal_asset_from_opportunity",
        "opportunity_used_asset",
    ):
        assert rt in RELATION_TYPES


def test_migration_mentions_asset_types():
    migration = Path(__file__).resolve().parents[1] / "alembic/versions/0008_proposal_intelligence_repository.py"
    text = migration.read_text(encoding="utf-8")
    for t in ASSET_TYPES:
        assert t in text
    for uk in USAGE_KINDS:
        assert uk in text
