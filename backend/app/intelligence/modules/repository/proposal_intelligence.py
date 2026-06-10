"""Repository: Proposal Intelligence — synthesize reusable proposal knowledge.

``repository.proposal_intelligence`` answers questions like "What transition
approaches have worked for CMS-like opportunities?" by combining the
deterministic Proposal Repository report with LLM synthesis.

Hard epistemic rule: observed patterns and historical correlations only —
never causal claims.
"""
from __future__ import annotations

from typing import Any

from app.intelligence.base import BaseIntelligenceModule, RAGContext
from app.schemas.proposal_repository import ProposalIntelligenceOutput


class ProposalIntelligenceModule(BaseIntelligenceModule):
    id = "repository.proposal_intelligence"
    group = "repository"
    label = "Proposal Intelligence"
    description = (
        "Synthesizes the Proposal Intelligence Repository into actionable "
        "observations: most successful win themes, transition and staffing "
        "approaches, agency-specific patterns, and reusable content "
        "recommendations. Every statement is Historical Evidence or clearly "
        "labeled inference — never causation."
    )
    version = "v1"
    prompt_id = "repository.proposal_intelligence"
    prompt_version = "v1"
    output_model = ProposalIntelligenceOutput
    retrieval_top_k = 8
    minimum_evidence = 0
    requires_customer_dna = False
    consumes_company_profile = False
    consumes_memory = True
    output_schema_summary = {
        "query_summary": "string",
        "relevant_assets": "[{title, asset_type, observation, ...}]",
        "agency_patterns": "string[]",
        "historical_observations": "string[]",
        "reusable_recommendations": "string[]",
        "confidence": "enum",
    }
    retrieval_query = (
        "win themes transition staffing executive summary past performance "
        "discriminator risk mitigation proposal approach"
    )

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        from app.services import proposal_repository_service

        report = await proposal_repository_service.build_report(
            self.db, workspace_id=ctx.workspace_id
        )
        return {"repository_report": report.model_dump(mode="json")}
