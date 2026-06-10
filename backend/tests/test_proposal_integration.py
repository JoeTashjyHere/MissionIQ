"""Proposal Intelligence Repository — module and consumption contracts."""
from __future__ import annotations

import json

from app.intelligence import get_registry
from app.intelligence.modules.capture.briefings import ExecutiveBriefModule
from app.intelligence.modules.capture.capability_match import CapabilityMatchModule
from app.intelligence.modules.capture.win_strategy import WinStrategyModule
from app.intelligence.modules.repository.proposal_intelligence import (
    ProposalIntelligenceModule,
)
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import _build_skeleton
from app.schemas.proposal_repository import ProposalIntelligenceOutput


def test_proposal_intelligence_module_registered():
    reg = get_registry()
    assert reg.get("repository.proposal_intelligence") is ProposalIntelligenceModule


def test_consuming_modules_declare_proposal_repository():
    assert WinStrategyModule.consumes_proposal_repository is True
    assert CapabilityMatchModule.consumes_proposal_repository is True
    assert ExecutiveBriefModule.consumes_proposal_repository is True


_OPP = {
    "name": "CMS Operations Support",
    "agency": "CMS",
    "sub_agency": None,
    "solicitation_number": None,
    "naics_code": None,
    "due_date": None,
    "estimated_value_cents": None,
    "incumbent": None,
    "notes": None,
    "capture_stage": "capture",
    "contract_vehicle": None,
}

_DNA = {
    "mission": "CMS mission systems.",
    "strategic_goals": ["Modernize ops"],
    "core_values": ["Continuity"],
    "success_metrics": ["Uptime"],
    "operational_challenges": ["Transition risk"],
    "technology_priorities": ["Cloud"],
    "risk_priorities": ["Disruption"],
    "stakeholder_concerns": ["Schedule"],
    "executive_summary": "Continuity through transition.",
    "confidence": "medium",
}


def test_win_strategy_prompt_includes_proposal_repository_block():
    lib = get_prompt_library()
    _, user, _ = lib.render(
        "capture.win_strategy",
        "v1",
        opportunity=_OPP,
        evidence=[],
        market_evidence=[],
        customer_dna=_DNA,
        company_profile=None,
        seller_incomplete=True,
        memory=None,
        proposal_repository={
            "asset_count": 1,
            "historical_assets": [
                {
                    "asset_type": "transition_approach",
                    "title": "Phased transition",
                    "summary": "90-day shadow period.",
                    "track_record": "Used in 3 pursuits · 2W–1L · 67% historical win rate",
                }
            ],
        },
        company_dna=None,
        capability_match=None,
        evaluation_criteria=None,
        risk_register=None,
    )
    assert "PROPOSAL REPOSITORY" in user
    assert "Phased transition" in user


def test_proposal_intelligence_stub_validates():
    user = "query_summary\nreusable_recommendations\nrepository_report"
    skeleton = _build_skeleton(user)
    ProposalIntelligenceOutput.model_validate({**skeleton, "__stub__": True})
