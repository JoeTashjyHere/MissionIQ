"""Capture: Capability Match.

The seller × customer fit engine. Compares the company against the
opportunity along five axes — Customer DNA, opportunity requirements,
evaluation criteria, market intelligence, and the Company Profile — and
returns a senior-capture-lead assessment of whether the company can credibly
win and deliver the work.

Requires Customer DNA. Consumes the Company Profile (optional, but flags
seller-side claims as assumptions when absent). Also pulls the latest
Evaluation Criteria analysis when one exists, for a sharper read on how the
bid will be scored.
"""
from __future__ import annotations

from typing import Any

from app.intelligence.base import BaseIntelligenceModule, RAGContext
from app.schemas.intelligence import CapabilityMatchOutput


class CapabilityMatchModule(BaseIntelligenceModule):
    id = "capture.capability_match"
    group = "capture"
    label = "Capability Match"
    description = (
        "Assess whether the company can credibly win and deliver: strong/weak "
        "fit, missing capabilities, required proof points, teaming "
        "recommendations, discriminators, reusable win themes, capture "
        "questions, and proposal risks tied to company gaps. Compares Customer "
        "DNA, requirements, evaluation criteria, market intelligence, and the "
        "Company Profile."
    )
    version = "v1"
    prompt_id = "capture.capability_match"
    prompt_version = "v1"
    output_model = CapabilityMatchOutput
    output_schema_summary = {
        "win_assessment": "string",
        "fit_score": "enum",
        "strong_fit_areas": "[{area, rationale, evidence_refs}]",
        "weak_fit_areas": "[{area, rationale, evidence_refs}]",
        "missing_capabilities": "string[]",
        "required_proof_points": "string[]",
        "recommended_teaming_partners": "[{partner_profile, fills_gap}]",
        "suggested_discriminators": "string[]",
        "reusable_win_themes": "string[]",
        "capture_questions": "string[]",
        "proposal_risks": "[{title, severity, mitigation}]",
    }
    retrieval_query = (
        "requirements scope evaluation factors staffing past performance "
        "transition security technical approach deliverables capabilities"
    )
    retrieval_top_k = 16
    minimum_evidence = 1
    requires_customer_dna = True
    consumes_company_profile = True
    consumes_proposal_repository = True

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Pull the latest Evaluation Criteria analysis if one exists so the
        fit assessment reflects how the bid will actually be scored."""
        evaluation_criteria = await self._load_latest_output(
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            module_id="capture.evaluation_criteria",
        )
        return {"evaluation_criteria": evaluation_criteria}
