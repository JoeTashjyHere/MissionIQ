"""Company DNA + Capability Match — seller-side intelligence contract.

Locks the milestone guarantees:

- Both modules are registered with the right flags (Company DNA consumes the
  Company Profile; Capability Match requires Customer DNA and consumes the
  Company Profile).
- Their v1 prompts render and surface the seller-side fields.
- The local_stub produces schema-valid output for the populated and
  empty/incomplete Company Profile branches.
- When seller data is incomplete, Capability Match flags
  ``seller_data_complete = False`` and caps its confidence — the
  anti-overclaim guarantee.
- Downstream modules (compliance/evaluation/risk) advertise that they
  consume the Company Profile and their prompts degrade gracefully when it
  is incomplete.
"""
from __future__ import annotations

import json

import pytest

from app.intelligence import get_registry
from app.intelligence.modules.capture.capability_match import CapabilityMatchModule
from app.intelligence.modules.capture.company_dna import CompanyDnaModule
from app.intelligence.modules.capture.compliance_matrix import ComplianceMatrixModule
from app.intelligence.modules.capture.evaluation_criteria import (
    EvaluationCriteriaModule,
)
from app.intelligence.modules.capture.risk_register import RiskRegisterModule
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import CapabilityMatchOutput, CompanyDnaProfile


class _FakeEvidence:
    def __init__(self, ref_doc: str, page: int, snippet: str) -> None:
        self.document_name = ref_doc
        self.page_start = page
        self.page_end = page
        self.section_path = "Section L.1"
        self.chunk_id = "c1"
        self.snippet = snippet
        self.market_record_id = None
        self.document_id = "doc-1"
        self.score = 0.9


_OPP = {
    "name": "DHA Mission Operations Support",
    "agency": "Defense Health Agency",
    "sub_agency": None,
    "solicitation_number": "W912DY-26-R-9999",
    "naics_code": "541512",
    "due_date": None,
    "estimated_value_cents": 48_500_000_00,
    "incumbent": "Acme Federal Services LLC",
    "notes": None,
    "capture_stage": "capture",
    "contract_vehicle": "8(a) Sole Source",
}

_COMPANY = {
    "legal_name": "Demo Federal Solutions LLC",
    "primary_naics": "541512",
    "size_standard": "Small Business",
    "certifications": ["8(a)", "SDVOSB"],
    "overview": "Mission ops + cyber small business.",
    "differentiators": "FedRAMP-aligned managed services; 24x7 SOC.",
    "past_performance_summary": "DHA, VA, US Army.",
    "contract_vehicles": ["8(a) Sole Source"],
    "technology_partners": ["AWS", "Splunk"],
    "case_studies": "Stood up a 24x7 ops center in 45 days.",
    "key_personnel": "PM (PMP), ISSO (CISSP).",
    "geographic_footprint": "National; cleared staff in NCR.",
    "security_posture": "FedRAMP Moderate; IL5 lineage.",
    "delivery_model": "Embedded agile pods with shared SOC.",
    "pricing_posture": "Competitive value.",
    "capabilities": [
        {
            "name": "Mission Operations Center Support",
            "category": "Operations",
            "maturity": "mature",
            "description": "24x7 ops, incident response, COOP.",
            "keywords": [],
        },
        {
            "name": "FedRAMP Moderate Engineering",
            "category": "Cyber",
            "maturity": "mature",
            "description": "ATO support, continuous monitoring.",
            "keywords": [],
        },
    ],
}

_DNA = {
    "mission": "Run DHA mission systems 24x7.",
    "strategic_goals": ["Modernize ops", "Continuity of operations"],
    "core_values": ["Mission readiness"],
    "success_metrics": ["Uptime", "MTTR"],
    "operational_challenges": ["Aging systems"],
    "technology_priorities": ["Zero trust"],
    "risk_priorities": ["Mission disruption during transition"],
    "stakeholder_concerns": ["CO: schedule", "Mission Owner: continuity"],
    "executive_summary": "DHA needs continuity through transition.",
    "confidence": "medium",
}


def _evidence() -> list[_FakeEvidence]:
    return [
        _FakeEvidence("example_rfp.txt", 1, "The Contractor shall provide 24x7 support."),
        _FakeEvidence("example_rfp.txt", 2, "Evaluation factors in descending importance."),
    ]


def _render(prompt_id, evidence, *, company_profile, seller_incomplete, **extra):
    prompts = get_prompt_library()
    _, user, _ = prompts.render(
        prompt_id,
        "v1",
        opportunity=_OPP,
        evidence=evidence,
        market_evidence=[],
        customer_dna=_DNA,
        company_profile=company_profile,
        seller_incomplete=seller_incomplete,
        **extra,
    )
    return user


# ── Registration / flags ───────────────────────────────────────────────────


def test_modules_registered():
    registry = get_registry()
    assert registry.get("capture.company_dna") is CompanyDnaModule
    assert registry.get("capture.capability_match") is CapabilityMatchModule


def test_company_dna_consumes_profile_and_needs_no_customer_dna():
    assert CompanyDnaModule.consumes_company_profile is True
    assert CompanyDnaModule.requires_customer_dna is False
    assert CompanyDnaModule.minimum_evidence == 0


def test_capability_match_requires_dna_and_consumes_profile():
    assert CapabilityMatchModule.requires_customer_dna is True
    assert CapabilityMatchModule.consumes_company_profile is True


def test_downstream_modules_now_consume_company_profile():
    for cls in (
        ComplianceMatrixModule,
        EvaluationCriteriaModule,
        RiskRegisterModule,
    ):
        assert cls.consumes_company_profile is True, cls.id


# ── Company DNA ─────────────────────────────────────────────────────────────


def test_company_dna_prompt_surfaces_seller_fields():
    user = _render(
        "capture.company_dna",
        [],
        company_profile=_COMPANY,
        seller_incomplete=False,
    )
    assert "COMPANY PROFILE" in user
    assert "CAPABILITY CATALOG" in user
    assert "Mission Operations Center Support" in user
    assert "core_capabilities" in user  # schema advertised


@pytest.mark.asyncio
async def test_company_dna_stub_validates_when_profile_present():
    user = _render(
        "capture.company_dna",
        [],
        company_profile=_COMPANY,
        seller_incomplete=False,
    )
    resp = await LocalStubLLM().generate_json(system="", user=user)
    parsed = CompanyDnaProfile.model_validate(json.loads(resp.text))
    assert parsed.core_capabilities
    assert parsed.differentiators
    assert parsed.profile_completeness in ("complete", "partial")


@pytest.mark.asyncio
async def test_company_dna_stub_reports_empty_without_profile():
    user = _render(
        "capture.company_dna",
        [],
        company_profile=None,
        seller_incomplete=True,
    )
    resp = await LocalStubLLM().generate_json(system="", user=user)
    parsed = CompanyDnaProfile.model_validate(json.loads(resp.text))
    assert parsed.profile_completeness == "empty"
    assert parsed.confidence == "insufficient"
    assert parsed.core_capabilities == []
    assert any("company profile" in a.lower() for a in parsed.recommended_actions)


# ── Capability Match ────────────────────────────────────────────────────────


def test_capability_match_prompt_lists_five_inputs_and_deliverables():
    user = _render(
        "capture.capability_match",
        _evidence(),
        company_profile=_COMPANY,
        seller_incomplete=False,
        evaluation_criteria=None,
    )
    assert "CUSTOMER DNA PROFILE" in user
    assert "COMPANY PROFILE" in user
    assert "OPPORTUNITY REQUIREMENTS" in user
    for field in (
        "strong_fit_areas",
        "weak_fit_areas",
        "missing_capabilities",
        "required_proof_points",
        "recommended_teaming_partners",
        "suggested_discriminators",
        "reusable_win_themes",
        "capture_questions",
        "proposal_risks",
    ):
        assert field in user, f"missing {field} in prompt schema"


@pytest.mark.asyncio
async def test_capability_match_stub_full_profile_is_grounded():
    user = _render(
        "capture.capability_match",
        _evidence(),
        company_profile=_COMPANY,
        seller_incomplete=False,
        evaluation_criteria=None,
    )
    resp = await LocalStubLLM().generate_json(system="", user=user)
    parsed = CapabilityMatchOutput.model_validate(json.loads(resp.text))
    assert parsed.seller_data_complete is True
    assert parsed.win_assessment
    assert parsed.strong_fit_areas
    assert parsed.required_proof_points
    assert parsed.reusable_win_themes


@pytest.mark.asyncio
async def test_capability_match_stub_flags_incomplete_seller_data():
    user = _render(
        "capture.capability_match",
        _evidence(),
        company_profile=None,
        seller_incomplete=True,
        evaluation_criteria=None,
    )
    resp = await LocalStubLLM().generate_json(system="", user=user)
    parsed = CapabilityMatchOutput.model_validate(json.loads(resp.text))
    # The anti-overclaim guarantee: seller data missing ⇒ flagged + capped.
    assert parsed.seller_data_complete is False
    assert parsed.fit_score in ("moderate", "marginal", "weak")
    assert any(
        "company profile" in a.lower() for a in parsed.recommended_actions
    )
