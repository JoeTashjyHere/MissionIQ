"""Capture: Outcome Intelligence.

``capture.outcome_intelligence`` answers one question: *what does our
organization's win/loss track record mean for THIS pursuit?*

It consumes the deterministic workspace outcome analysis (recorded outcomes,
win/loss patterns, agency and competitor trends — all observed statistics
with source pursuits) plus Pursuit Memory, and synthesizes strategic
recommendations for the current pursuit.

Hard epistemic rule: track records are observed patterns and historical
correlations. The module reports what was observed and what it implies as
clearly-labeled inference — it never claims a pattern *caused* a win or loss.
"""
from __future__ import annotations

from typing import Any

from app.intelligence.base import BaseIntelligenceModule, RAGContext
from app.schemas.intelligence import OutcomeIntelligenceOutput


class OutcomeIntelligenceModule(BaseIntelligenceModule):
    id = "capture.outcome_intelligence"
    label = "Outcome Intelligence"
    description = (
        "Applies the organization's recorded win/loss history to this pursuit: "
        "which observed win patterns are present here, which loss patterns "
        "recur, the agency and competitor track records, and what they imply "
        "as strategic recommendations. Every statement is tagged Evidence, "
        "Inference, or Assumption; patterns are reported as observed patterns "
        "and historical correlations — never causation."
    )
    group = "capture"
    version = "v1"
    prompt_id = "capture.outcome_intelligence"
    prompt_version = "v1"
    output_model = OutcomeIntelligenceOutput
    retrieval_top_k = 10
    minimum_evidence = 0
    # Runs on any pursuit — the track record matters most precisely when the
    # current opportunity's own intelligence is still thin.
    requires_customer_dna = False
    consumes_company_profile = False
    consumes_memory = True
    output_schema_summary = {
        "outcome_context_summary": "string",
        "relevant_win_patterns": "[{statement, basis, sources}]",
        "relevant_loss_patterns": "[{statement, basis, sources}]",
        "agency_track_record": "[{statement, basis, sources}]",
        "competitor_track_record": "[{statement, basis, sources}]",
        "strategic_recommendations": "[{action, rationale, priority}]",
        "confidence": "{level, score, rationale}",
        "historical_evidence": "{similar_opps[], win_themes[], risks[], ...}",
    }
    retrieval_query = (
        "win themes discriminators competition incumbent risk capability "
        "agency past performance evaluation"
    )

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        # Imported lazily: the service pulls schemas + graph, neither of which
        # should be imported at intelligence-module import time.
        from app.services import outcome_intelligence_service

        outcome_context = await outcome_intelligence_service.workspace_outcome_context(
            self.db, workspace_id=ctx.workspace_id
        )
        win_strategy = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.win_strategy",
        )
        return {"outcome_context": outcome_context, "win_strategy": win_strategy}
