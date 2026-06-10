"""Executive Briefings & Gate Reviews — leadership deliverable contracts.

Locks the guarantees that make these decision packages rather than summaries:

- All three modules are registered, require Customer DNA, consume the Company
  Profile and Pursuit Memory, and pull every upstream synthesis output.
- Each prompt presents the synthesis inputs, asks for a DECISION, and demands
  Evidence / Inference / Assumption tagging plus Historical Evidence from memory.
- The local stub produces schema-valid output for each module.
- With partial inputs, confidence is dampened and inputs_missing is recorded.
- Pursuit Memory flows through as Historical Evidence.
"""
from __future__ import annotations

import json

import pytest

from app.intelligence import get_registry
from app.intelligence.modules.capture.briefings import (
    BidDecisionModule,
    ExecutiveBriefModule,
    GateReviewModule,
)
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import (
    BidDecisionOutput,
    ExecutiveBriefOutput,
    GateReviewOutput,
)


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
    "due_date": "2026-09-01",
    "estimated_value_cents": 48_500_000_00,
    "incumbent": "Acme Federal Services LLC",
    "notes": None,
    "capture_stage": "capture",
    "contract_vehicle": "8(a) Sole Source",
    "set_aside": "8(a)",
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
    "agency": "Defense Health Agency",
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
    "missing_capabilities": ["DHA past performance"],
    "suggested_discriminators": ["45-day stand-up"],
}

_EVAL = {
    "likely_decision_drivers": ["Transition risk"],
    "potential_discriminators": ["Security posture"],
}

_RISK = {"top_risks": ["Incumbent continuity advantage"]}

_WIN_STRATEGY = {
    "pursuit_recommendation": "pursue",
    "executive_pursuit_recommendation": "Pursue as a modernization play.",
    "win_confidence_assessment": {
        "level": "medium",
        "score": 58,
        "rationale": "Strong fit, past-performance gap.",
        "key_drivers": [],
    },
    "key_discriminators": [
        {"statement": "Zero-downtime transition", "basis": "inference", "sources": []}
    ],
    "win_themes": [
        {"statement": "Mission continuity", "basis": "inference", "sources": []}
    ],
}

_MEMORY = {
    "summary": "MissionIQ recalled 2 similar prior pursuits for DHA.",
    "similar_count": 2,
    "similar_opportunities": [
        {"name": "DHA SOC Recompete", "agency": "DHA", "reasons": ["Same agency"]}
    ],
    "prior_risks": [{"label": "Aggressive transition timeline", "frequency": 3}],
    "prior_discriminators": [{"label": "Cleared 24x7 SOC bench", "frequency": 2}],
    "prior_win_themes": [{"label": "Zero-downtime transition", "frequency": 2}],
    "inferences": ["Treat the transition timeline as a standing risk."],
}


def _evidence():
    return [
        _FakeEvidence(1, "The Contractor shall provide 24x7 operations."),
        _FakeEvidence(2, "Evaluation factors in descending order of importance."),
    ]


def _render(prompt_id: str, *, full: bool, memory: dict | None = None):
    prompts = get_prompt_library()
    _, user, _ = prompts.render(
        prompt_id,
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
        win_strategy=_WIN_STRATEGY if full else None,
        proposal_repository=None,
    )
    return user


def _stub(prompt_id: str, *, full: bool, memory: dict | None = None) -> dict:
    import anyio

    user = _render(prompt_id, full=full, memory=memory)
    llm = LocalStubLLM()
    resp = anyio.run(
        lambda: llm.generate_json(system="s", user=user)  # type: ignore[arg-type]
    )
    return json.loads(resp.text)


_MODULES = [
    (ExecutiveBriefModule, "capture.executive_brief", ExecutiveBriefOutput),
    (GateReviewModule, "capture.gate_review", GateReviewOutput),
    (BidDecisionModule, "capture.bid_decision", BidDecisionOutput),
]


# ── Registration / flags ───────────────────────────────────────────────────


@pytest.mark.parametrize("module,module_id,_model", _MODULES)
def test_briefing_module_registered_with_flags(module, module_id, _model):
    assert get_registry().get(module_id) is module
    assert module.requires_customer_dna is True
    assert module.consumes_company_profile is True
    assert module.consumes_memory is True


# ── Prompts are decisions, not summaries ───────────────────────────────────


def test_executive_brief_prompt_demands_decision_and_basis():
    user = _render("capture.executive_brief", full=True, memory=_MEMORY)
    assert "WIN STRATEGY" in user
    assert "PURSUIT MEMORY" in user
    assert "DHA SOC Recompete" in user  # memory flows in
    # The schema demands the six sections + recommendation.
    assert "opportunity_snapshot" in user
    assert "executive_recommendation" in user
    assert "historical_evidence" in user


def test_gate_review_prompt_demands_scores_and_escalations():
    user = _render("capture.gate_review", full=True, memory=_MEMORY)
    assert "attractiveness_score" in user
    assert "probability_of_win" in user
    assert "escalations" in user


def test_bid_decision_prompt_demands_six_factors():
    prompts = get_prompt_library()
    system, user, _ = prompts.render(
        "capture.bid_decision",
        "v1",
        opportunity=_OPP,
        evidence=_evidence(),
        market_evidence=[],
        customer_dna=_DNA,
        company_profile=None,
        seller_incomplete=False,
        memory=_MEMORY,
        company_dna=_COMPANY_DNA,
        capability_match=_CAP_MATCH,
        evaluation_criteria=_EVAL,
        risk_register=_RISK,
        win_strategy=_WIN_STRATEGY,
    )
    # The six canonical factors are named in the instructions.
    assert "Strategic Alignment" in system
    assert "Delivery Readiness" in system
    # The decision-oriented schema fields are requested in the user prompt.
    assert "required_next_steps" in user
    assert "decision_drivers" in user


# ── Stub output is schema-valid for each module ─────────────────────────────


@pytest.mark.parametrize("module,module_id,model", _MODULES)
def test_stub_output_is_schema_valid(module, module_id, model):
    payload = _stub(module_id, full=True, memory=_MEMORY)
    obj = model.model_validate(payload)  # raises on invalid
    assert obj is not None


# ── Memory flows through as Historical Evidence ─────────────────────────────


@pytest.mark.parametrize("module,module_id,model", _MODULES)
def test_memory_populates_historical_evidence(module, module_id, model):
    with_mem = model.model_validate(_stub(module_id, full=True, memory=_MEMORY))
    without_mem = model.model_validate(_stub(module_id, full=True, memory=None))
    he_with = with_mem.historical_evidence
    he_without = without_mem.historical_evidence
    assert he_with.similar_opportunities  # populated from memory
    assert not he_without.similar_opportunities  # empty without memory


# ── Partial inputs dampen confidence and record what's missing ─────────────


def test_executive_brief_partial_inputs_record_missing_and_dampen():
    full = ExecutiveBriefOutput.model_validate(
        _stub("capture.executive_brief", full=True, memory=_MEMORY)
    )
    partial = ExecutiveBriefOutput.model_validate(
        _stub("capture.executive_brief", full=False, memory=None)
    )
    assert partial.inputs_missing  # records what's missing
    assert not full.inputs_missing
    assert (
        partial.executive_recommendation.confidence_score
        < full.executive_recommendation.confidence_score
    )


def test_gate_review_partial_inputs_lower_pwin():
    full = GateReviewOutput.model_validate(
        _stub("capture.gate_review", full=True, memory=_MEMORY)
    )
    partial = GateReviewOutput.model_validate(
        _stub("capture.gate_review", full=False, memory=None)
    )
    assert partial.inputs_missing
    assert partial.probability_of_win.score < full.probability_of_win.score


def test_bid_decision_partial_inputs_lower_confidence_and_factor_basis():
    full = BidDecisionOutput.model_validate(
        _stub("capture.bid_decision", full=True, memory=_MEMORY)
    )
    partial = BidDecisionOutput.model_validate(
        _stub("capture.bid_decision", full=False, memory=None)
    )
    assert partial.inputs_missing
    assert partial.confidence.score < full.confidence.score
    # The six canonical factors are always scored.
    names = {f.name for f in full.factors}
    assert {
        "Strategic Alignment",
        "Revenue Potential",
        "Relationship Position",
        "Competitive Position",
        "Delivery Readiness",
        "Risk Profile",
    } <= names
