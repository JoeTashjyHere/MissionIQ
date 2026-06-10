"""Capture: Win Strategy Engine — the flagship MissionIQ deliverable.

This is the culminating synthesis module. It does NOT summarize documents.
It assembles everything MissionIQ knows about a pursuit — Customer DNA,
Company DNA, opportunity documents, evaluation criteria, Capability Match,
market intelligence, and the Risk Register — and produces a senior-capture-
executive gate-review assessment with strategic recommendations.

Dependencies
------------
- Requires the Customer DNA Profile (hard prerequisite via the base class).
- Optionally consumes the Company Profile + the latest Company DNA,
  Capability Match, Evaluation Criteria, and Risk Register outputs. Each is
  optional: when absent, the prompt downgrades the affected conclusions to
  inference/assumption and records the gap in ``inputs_missing`` so a gate
  review knows the synthesis was run with partial inputs.
"""
from __future__ import annotations

from typing import Any

from app.intelligence.base import BaseIntelligenceModule, RAGContext
from app.schemas.intelligence import WinStrategyOutput


class WinStrategyModule(BaseIntelligenceModule):
    id = "capture.win_strategy"
    group = "capture"
    label = "Win Strategy"
    description = (
        "The flagship deliverable. Synthesizes Customer DNA, Company DNA, "
        "opportunity documents, evaluation criteria, Capability Match, market "
        "intelligence, and risks into a senior-capture-executive gate-review "
        "assessment: pursuit recommendation, strengths, weaknesses, "
        "discriminators, black-hat view, evaluator concerns, win themes, "
        "competitive assessment, critical capture actions, and win confidence."
    )
    version = "v1"
    prompt_id = "capture.win_strategy"
    prompt_version = "v1"
    output_model = WinStrategyOutput
    output_schema_summary = {
        "executive_pursuit_recommendation": "string",
        "pursuit_recommendation": "enum",
        "strengths": "[{statement, basis, sources}]",
        "weaknesses": "[{statement, basis, sources}]",
        "key_discriminators": "[{statement, basis, sources}]",
        "black_hat_assessment": "[{competitor_move, our_counter}]",
        "likely_evaluator_concerns": "[{statement, basis, sources}]",
        "win_themes": "[{statement, basis, sources}]",
        "competitive_assessment": "{summary, competitors[]}",
        "critical_capture_actions": "[{action, priority, rationale}]",
        "win_confidence_assessment": "{level, score, rationale}",
    }
    retrieval_query = (
        "mission scope evaluation factors discriminators incumbent competition "
        "past performance staffing transition risk pricing win themes objectives"
    )
    retrieval_top_k = 18
    minimum_evidence = 1
    requires_customer_dna = True
    consumes_company_profile = True
    # Consume institutional memory: prior risks, discriminators, and win
    # themes recalled from similar pursuits are folded in as Historical
    # Evidence so the strategy gets sharper with every opportunity processed.
    consumes_memory = True
    consumes_proposal_repository = True

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Load every upstream synthesis output the Win Strategy reasons over.

        All are optional. The prompt records which were present
        (``inputs_used``) vs missing (``inputs_missing``) so the gate review
        can calibrate confidence.
        """
        company_dna = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.company_dna",
        )
        capability_match = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.capability_match",
        )
        evaluation_criteria = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.evaluation_criteria",
        )
        risk_register = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.risk_register",
        )
        return {
            "company_dna": company_dna,
            "capability_match": capability_match,
            "evaluation_criteria": evaluation_criteria,
            "risk_register": risk_register,
        }
