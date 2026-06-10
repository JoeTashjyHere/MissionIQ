"""capture.outcome_intelligence — module contract tests.

Locks the closed-loop guarantees:

- The module is registered, consumes Pursuit Memory, and runs WITHOUT a
  Customer DNA Profile (the track record matters most when intelligence is
  thin).
- The prompt presents the deterministic outcome analysis, demands basis
  tagging, and hard-forbids causal claims.
- The local stub produces schema-valid output, honestly handles the
  no-history case, and never uses causal language.
- The compact memory dict passed to ALL consumes_memory modules carries
  track records once outcomes exist.
"""
from __future__ import annotations

import json

from app.intelligence import get_registry
from app.intelligence.modules.capture.outcome_intelligence import (
    OutcomeIntelligenceModule,
)
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import _build_skeleton
from app.schemas.intelligence import OutcomeIntelligenceOutput

CAUSAL_PHRASES = ("caused the win", "because of", "leads to wins", "led to the loss")

_OPP = {
    "name": "DHA Mission Operations Support",
    "agency": "Defense Health Agency",
    "contract_vehicle": None,
    "incumbent": None,
    "estimated_value_cents": None,
}

_OUTCOME_CONTEXT = {
    "summary": {"recorded": 5, "decided": 4, "wins": 3, "losses": 1, "win_rate": 0.75},
    "win_patterns": [
        {
            "label": "Mission continuity",
            "entity_type": "win_theme",
            "wins": 3,
            "losses": 0,
            "win_rate": 1.0,
            "observation": "'Mission continuity' appeared in 3 won and 0 lost pursuit(s) (100% historical win rate).",
        }
    ],
    "loss_patterns": [],
    "agency_trends": [],
    "competitor_trends": [],
    "loss_factors": [{"factor": "price", "in_wins": 0, "in_losses": 2}],
    "observations": ["4 decided pursuit(s) recorded."],
}

_MEMORY = {
    "summary": "MissionIQ recalled 2 similar prior pursuits.",
    "similar_opportunities": [],
    "prior_win_themes": [
        {
            "label": "Mission continuity",
            "frequency": 2,
            "basis": "historical",
            "track_record": "3W–0L · 100% historical win rate",
        }
    ],
    "prior_discriminators": [],
    "prior_risks": [],
    "inferences": [],
}


def _render(outcome_context, memory):
    lib = get_prompt_library()
    return lib.render(
        "capture.outcome_intelligence",
        "v1",
        opportunity=_OPP,
        evidence=[],
        market_evidence=[],
        customer_dna=None,
        company_profile=None,
        seller_incomplete=False,
        memory=memory,
        outcome_context=outcome_context,
        win_strategy=None,
    )


def test_module_registered_with_learning_loop_flags():
    registry = get_registry()
    cls = registry.get("capture.outcome_intelligence")
    assert cls is OutcomeIntelligenceModule
    # Must run on ANY pursuit — no Customer DNA gate.
    assert cls.requires_customer_dna is False
    # Consumes the institutional memory layer.
    assert cls.consumes_memory is True
    assert cls.output_model is OutcomeIntelligenceOutput


def test_prompt_forbids_causation_and_demands_basis_tagging():
    tmpl = get_prompt_library().load("capture.outcome_intelligence", "v1")
    system = tmpl.system
    assert "NEVER CLAIM CAUSATION" in system
    assert "HISTORICAL CORRELATIONS" in system
    assert '"evidence"' in system and '"assumption"' in system
    # The honesty rule for the empty state.
    assert "NEVER invent a track record" in system


def test_prompt_renders_outcome_analysis_and_track_records():
    _, user, _ = _render(_OUTCOME_CONTEXT, _MEMORY)
    assert "OBSERVED WIN PATTERNS" in user
    assert "3 won, 1 lost" in user
    assert "75% historical win rate" in user
    # Memory items carry their track records into the prompt.
    assert "[3W–0L · 100% historical win rate]" in user


def test_prompt_flags_missing_history_honestly():
    _, user, _ = _render(None, None)
    assert "no pursuit outcomes recorded yet" in user


def test_stub_output_is_schema_valid_with_history():
    _, user, _ = _render(_OUTCOME_CONTEXT, _MEMORY)
    out = _build_skeleton(user)
    parsed = OutcomeIntelligenceOutput.model_validate(out)
    assert parsed.relevant_win_patterns
    assert parsed.strategic_recommendations
    assert "outcome_history" not in parsed.inputs_missing
    text = json.dumps(out).lower()
    for phrase in CAUSAL_PHRASES:
        assert phrase not in text


def test_stub_handles_no_history_without_inventing_a_track_record():
    _, user, _ = _render(None, None)
    out = _build_skeleton(user)
    parsed = OutcomeIntelligenceOutput.model_validate(out)
    assert parsed.inputs_missing == ["outcome_history"]
    assert parsed.relevant_win_patterns == []
    assert parsed.relevant_loss_patterns == []
    assert parsed.confidence.level == "low"


def test_base_memory_dict_exposes_track_records_to_all_modules():
    """The compact memory view every consumes_memory module receives must
    carry track_record when present — this is how Win Strategy and the
    briefings get outcome-weighted Historical Evidence without code changes."""
    import inspect

    from app.intelligence import base

    src = inspect.getsource(base.BaseIntelligenceModule._load_pursuit_memory)
    assert "track_record" in src
