"""Win Strategy Engine — the flagship synthesis contract.

Locks the guarantees that make this a gate-review deliverable rather than a
document summary:

- Registered, requires Customer DNA (hard prerequisite), consumes the
  Company Profile, and pulls every upstream synthesis output via
  ``extra_context``.
- The prompt presents all synthesis inputs and asks for the ten gate-review
  sections, NOT a summary.
- The local_stub produces schema-valid output with all ten sections.
- Epistemic basis is honored: points are tagged evidence / inference /
  assumption, and evidence-tagged points carry sources.
- With partial inputs, confidence is dampened and the missing inputs are
  recorded — the synthesis never fakes ``evidence`` it does not have.
"""
from __future__ import annotations

import json

import pytest

from app.intelligence import get_registry
from app.intelligence.modules.capture.win_strategy import WinStrategyModule
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import WinStrategyOutput


class _FakeEvidence:
    def __init__(self, page: int, snippet: str) -> None:
        self.document_name = "example_rfp.txt"
        self.page_start = page
        self.page_end = page
        self.section_path = "Section M"
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

_DNA = {
    "mission": "Run DHA mission systems 24x7.",
    "strategic_goals": ["Modernize ops"],
    "core_values": ["Mission readiness"],
    "success_metrics": ["Uptime"],
    "operational_challenges": ["Aging systems"],
    "technology_priorities": ["Zero trust"],
    "risk_priorities": ["Disruption during transition"],
    "stakeholder_concerns": ["CO: schedule"],
    "executive_summary": "Continuity through transition.",
    "confidence": "medium",
}

_COMPANY_DNA = {
    "company_summary": "Mission ops + cyber small business.",
    "core_capabilities": ["MOC support", "FedRAMP engineering"],
    "differentiators": ["SOC-embedded data engineering"],
    "past_performance": ["DHA ops"],
}

_CAP_MATCH = {
    "win_assessment": "Credible win with teaming.",
    "fit_score": "strong",
    "seller_data_complete": True,
    "missing_capabilities": ["DHA past performance"],
    "suggested_discriminators": ["45-day stand-up"],
}

_EVAL = {
    "evaluation_intelligence": "LPTA-leaning best value.",
    "likely_decision_drivers": ["Transition risk"],
    "potential_discriminators": ["Security posture"],
}

_RISK = {"top_risks": ["Incumbent continuity advantage"]}


def _evidence():
    return [
        _FakeEvidence(1, "The Contractor shall provide 24x7 operations."),
        _FakeEvidence(2, "Evaluation factors in descending order of importance."),
    ]


def _render(*, full: bool, memory: dict | None = None):
    prompts = get_prompt_library()
    _, user, _ = prompts.render(
        "capture.win_strategy",
        "v1",
        opportunity=_OPP,
        evidence=_evidence(),
        market_evidence=[_FakeEvidence(3, "Market: 6 likely bidders.")] if full else [],
        customer_dna=_DNA,
        company_profile=None,
        seller_incomplete=not full,
        memory=memory,
        company_dna=_COMPANY_DNA if full else None,
        capability_match=_CAP_MATCH if full else None,
        evaluation_criteria=_EVAL if full else None,
        risk_register=_RISK if full else None,
    )
    return user


# ── Registration / flags ───────────────────────────────────────────────────


def test_win_strategy_registered_with_flags():
    assert get_registry().get("capture.win_strategy") is WinStrategyModule
    assert WinStrategyModule.requires_customer_dna is True
    assert WinStrategyModule.consumes_company_profile is True
    assert WinStrategyModule.consumes_memory is True


def test_prompt_folds_in_pursuit_memory_as_historical_evidence():
    memory = {
        "summary": "MissionIQ recalled 2 similar prior pursuit(s) for DHS.",
        "similar_count": 2,
        "similar_opportunities": [
            {"name": "DHS SOC Recompete", "agency": "DHS", "reasons": ["Same agency: DHS"]}
        ],
        "prior_risks": [{"label": "Aggressive transition timeline", "frequency": 3, "basis": "historical"}],
        "prior_discriminators": [{"label": "Cleared 24x7 SOC bench", "frequency": 2, "basis": "historical"}],
        "prior_win_themes": [{"label": "Zero-downtime transition", "frequency": 2, "basis": "historical"}],
        "inferences": ["Treat the transition timeline as a standing risk."],
    }
    user = _render(full=True, memory=memory)
    assert "PURSUIT MEMORY" in user
    assert "Aggressive transition timeline" in user
    assert "Zero-downtime transition" in user
    assert "Historical Evidence" in user
    # No history → graceful net-new message.
    empty = _render(full=True, memory=None)
    assert "no prior pursuit history yet" in empty.lower()


# ── Prompt is synthesis, not summary ───────────────────────────────────────


def test_prompt_demands_synthesis_and_basis_tagging():
    user = _render(full=True)
    # The synthesis inputs are present...
    assert "CUSTOMER DNA PROFILE" in user
    assert "COMPANY DNA PROFILE" in user
    assert "CAPABILITY MATCH" in user
    assert "EVALUATION CRITERIA" in user
    assert "RISK REGISTER" in user
    # ...and all ten gate-review sections are requested.
    for field in (
        "executive_pursuit_recommendation",
        "strengths",
        "weaknesses",
        "key_discriminators",
        "black_hat_assessment",
        "likely_evaluator_concerns",
        "win_themes",
        "competitive_assessment",
        "critical_capture_actions",
        "win_confidence_assessment",
    ):
        assert field in user, f"missing {field}"
    # The basis vocabulary is enforced.
    assert "evidence" in user and "inference" in user and "assumption" in user


def test_prompt_marks_missing_inputs_when_partial():
    user = _render(full=False)
    assert "CAPABILITY MATCH: *** MISSING" in user
    assert "EVALUATION CRITERIA: *** MISSING" in user
    assert "RISK REGISTER: *** MISSING" in user


# ── Stub output is schema-valid and honest ─────────────────────────────────


@pytest.mark.asyncio
async def test_stub_full_inputs_schema_valid_and_complete():
    resp = await LocalStubLLM().generate_json(system="", user=_render(full=True))
    o = WinStrategyOutput.model_validate(json.loads(resp.text))
    assert o.executive_pursuit_recommendation
    assert o.pursuit_recommendation in ("pursue", "pursue_with_conditions", "no_bid")
    assert o.strengths and o.weaknesses and o.key_discriminators
    assert o.black_hat_assessment
    assert o.competitive_assessment.competitors
    assert o.critical_capture_actions
    assert o.win_confidence_assessment.score >= 0
    assert "Company DNA" in o.inputs_used
    assert o.inputs_missing == []


@pytest.mark.asyncio
async def test_stub_tags_basis_and_sources():
    resp = await LocalStubLLM().generate_json(system="", user=_render(full=True))
    o = WinStrategyOutput.model_validate(json.loads(resp.text))
    bases = {p.basis for p in o.strengths + o.weaknesses + o.key_discriminators}
    # All three epistemic levels appear across the assessment.
    assert {"evidence", "inference", "assumption"} & bases
    # Evidence-tagged points must cite at least one source.
    for p in o.strengths + o.key_discriminators:
        if p.basis == "evidence":
            assert p.sources, f"evidence point without sources: {p.statement}"


@pytest.mark.asyncio
async def test_stub_dampens_confidence_with_partial_inputs():
    full = WinStrategyOutput.model_validate(
        json.loads((await LocalStubLLM().generate_json(system="", user=_render(full=True))).text)
    )
    partial = WinStrategyOutput.model_validate(
        json.loads((await LocalStubLLM().generate_json(system="", user=_render(full=False))).text)
    )
    assert partial.win_confidence_assessment.score < full.win_confidence_assessment.score
    assert "Company DNA" in partial.inputs_missing
    assert "Capability Match" in partial.inputs_missing
