"""Downstream Capture modules — DNA dependency, prompt rendering, stub output.

These tests lock the anti-generic-AI contract:

1. Compliance Matrix, Evaluation Criteria, and Risk Register all advertise
   ``requires_customer_dna = True``.
2. The prompt library renders each module's v1 prompt with a Customer DNA
   block injected as Jinja context, and the rendered prompt surfaces the
   DNA fields the LLM is expected to reason over.
3. The local_stub LLM, when fed the rendered prompt + a fake DNA block,
   returns JSON that validates against each module's Pydantic schema and
   carries the insight-grade fields (why/mission alignment/customer
   priority on compliance; evaluation_intelligence + decision drivers on
   evaluation; lane categorization + mission_impact on risks).
"""
from __future__ import annotations

import json

import pytest

from app.intelligence import get_registry
from app.intelligence.modules.capture.compliance_matrix import (
    ComplianceMatrixModule,
)
from app.intelligence.modules.capture.evaluation_criteria import (
    EvaluationCriteriaModule,
)
from app.intelligence.modules.capture.risk_register import RiskRegisterModule
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import (
    ComplianceMatrixOutput,
    EvaluationCriteriaOutput,
    RiskRegisterOutput,
)


class _FakeEvidence:
    def __init__(
        self,
        chunk_id: str,
        document_name: str,
        page_start: int,
        section_path: str | None,
        snippet: str,
    ) -> None:
        self.chunk_id = chunk_id
        self.document_name = document_name
        self.page_start = page_start
        self.page_end = page_start
        self.section_path = section_path
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
    "capture_stage": "qualification",
    "contract_vehicle": "GSA OASIS+",
}

_FAKE_DNA = {
    "mission": "Provide 24x7 mission-system operations for the Defense Health Agency.",
    "strategic_goals": [
        "Modernize mission operations infrastructure",
        "Strengthen continuity-of-operations",
        "Accelerate FedRAMP-aligned cloud adoption",
    ],
    "core_values": ["Mission readiness", "Auditability", "Workforce stewardship"],
    "success_metrics": ["Mission system uptime", "MTTR reduction"],
    "operational_challenges": ["Aging mission systems", "Limited cyber engineering capacity"],
    "technology_priorities": ["Zero-trust architecture", "Observability dashboards"],
    "risk_priorities": ["Mission disruption during transition", "OIG findings"],
    "stakeholder_concerns": [
        "Contracting Officer: schedule certainty",
        "Mission Owner: continuity of operations",
    ],
    "executive_summary": "DHA needs a partner that can keep mission systems running through transition without OIG findings.",
    "confidence": "medium",
}


def _render(prompt_id: str, prompt_version: str, evidence: list[_FakeEvidence]) -> str:
    prompts = get_prompt_library()
    _, user, _ = prompts.render(
        prompt_id,
        prompt_version,
        opportunity=_OPP,
        evidence=evidence,
        market_evidence=[],
        customer_dna=_FAKE_DNA,
    )
    return user


def _evidence() -> list[_FakeEvidence]:
    return [
        _FakeEvidence(
            chunk_id="c1",
            document_name="example_rfp.txt",
            page_start=1,
            section_path="Section L.3.1",
            snippet="The Contractor shall provide 24x7 operational support.",
        ),
        _FakeEvidence(
            chunk_id="c2",
            document_name="example_rfp.txt",
            page_start=2,
            section_path="Section M.2",
            snippet="Evaluation factors in descending order of importance.",
        ),
    ]


# ── Registry / dependency contracts ────────────────────────────────────────


def test_all_downstream_modules_registered():
    registry = get_registry()
    for module_id in (
        "capture.compliance_matrix",
        "capture.evaluation_criteria",
        "capture.risk_register",
    ):
        assert registry.get(module_id) is not None, module_id


def test_all_downstream_modules_require_customer_dna():
    for cls in (
        ComplianceMatrixModule,
        EvaluationCriteriaModule,
        RiskRegisterModule,
    ):
        assert cls.requires_customer_dna is True, cls.id


# ── Compliance Matrix ──────────────────────────────────────────────────────


def test_compliance_prompt_surfaces_dna_block():
    user = _render(
        ComplianceMatrixModule.prompt_id,
        ComplianceMatrixModule.prompt_version,
        _evidence(),
    )
    assert "CUSTOMER DNA PROFILE" in user
    assert "Strategic goals" in user
    assert "why_requirement_exists" in user
    assert "mission_alignment" in user
    assert "customer_priority" in user


@pytest.mark.asyncio
async def test_compliance_stub_emits_insight_grade_rows():
    user = _render(
        ComplianceMatrixModule.prompt_id,
        ComplianceMatrixModule.prompt_version,
        _evidence(),
    )
    stub = LocalStubLLM()
    resp = await stub.generate_json(system="", user=user)
    payload = json.loads(resp.text)
    parsed = ComplianceMatrixOutput.model_validate(payload)
    assert parsed.rows, "stub should emit at least one compliance row"
    for row in parsed.rows:
        assert row.requirement_id
        assert row.requirement_text
        assert row.why_requirement_exists
        assert row.mission_alignment
        assert row.customer_priority in ("critical", "high", "medium", "low")


# ── Evaluation Criteria ────────────────────────────────────────────────────


def test_evaluation_prompt_surfaces_dna_and_insight_fields():
    user = _render(
        EvaluationCriteriaModule.prompt_id,
        EvaluationCriteriaModule.prompt_version,
        _evidence(),
    )
    assert "CUSTOMER DNA PROFILE" in user
    assert "evaluation_intelligence" in user
    assert "likely_decision_drivers" in user
    assert "potential_discriminators" in user
    assert "potential_weaknesses" in user
    assert "strategic_recommendations" in user


@pytest.mark.asyncio
async def test_evaluation_stub_emits_evaluation_intelligence():
    user = _render(
        EvaluationCriteriaModule.prompt_id,
        EvaluationCriteriaModule.prompt_version,
        _evidence(),
    )
    stub = LocalStubLLM()
    resp = await stub.generate_json(system="", user=user)
    payload = json.loads(resp.text)
    parsed = EvaluationCriteriaOutput.model_validate(payload)
    assert parsed.factors
    assert parsed.evaluation_intelligence
    assert parsed.likely_decision_drivers
    assert parsed.potential_discriminators
    assert parsed.potential_weaknesses
    assert parsed.strategic_recommendations


# ── Risk Register ──────────────────────────────────────────────────────────


def test_risk_prompt_surfaces_dna_and_lane_taxonomy():
    user = _render(
        RiskRegisterModule.prompt_id,
        RiskRegisterModule.prompt_version,
        _evidence(),
    )
    assert "CUSTOMER DNA PROFILE" in user
    # All four lanes must be advertised in the prompt
    assert "capture_risks" in user
    assert "proposal_risks" in user
    assert "delivery_risks" in user
    assert "customer_risks" in user
    # Required per-risk fields
    assert "mission_impact" in user
    assert "probability" in user
    assert "severity" in user
    assert "mitigation" in user
    assert "supporting_evidence" in user


@pytest.mark.asyncio
async def test_risk_stub_emits_categorized_risks_with_mission_impact():
    user = _render(
        RiskRegisterModule.prompt_id,
        RiskRegisterModule.prompt_version,
        _evidence(),
    )
    stub = LocalStubLLM()
    resp = await stub.generate_json(system="", user=user)
    payload = json.loads(resp.text)
    parsed = RiskRegisterOutput.model_validate(payload)
    # The stub fills every lane for a healthy demo; at minimum every lane key
    # must be present (even if some are empty) and at least one risk total
    # should exist.
    total = (
        len(parsed.capture_risks)
        + len(parsed.proposal_risks)
        + len(parsed.delivery_risks)
        + len(parsed.customer_risks)
    )
    assert total > 0
    for risk in parsed.capture_risks + parsed.delivery_risks:
        assert risk.title
        assert risk.mission_impact
        assert risk.mitigation
        assert risk.probability in {"low", "medium", "high"}
        assert risk.severity in {"low", "medium", "high", "critical"}
