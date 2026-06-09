"""Capture: Opportunity Summary.

Reference implementation. New modules follow the same ~30-line pattern:
declare class-level metadata, optionally override `output_model` for stricter
validation, and (rarely) override `run()` for non-default orchestration.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import OpportunitySummaryOutput


class OpportunitySummaryModule(BaseIntelligenceModule):
    id = "capture.opportunity_summary"
    group = "capture"
    label = "Opportunity Summary"
    description = (
        "Executive briefing of the opportunity: mission need, scope, deliverables, "
        "timeline, risks, and pursue/no-pursue indicators with source citations."
    )
    version = "v1"
    prompt_id = "capture.opportunity_summary"
    prompt_version = "v1"
    output_model = OpportunitySummaryOutput
    output_schema_summary = {
        "executive_summary": "string",
        "key_findings": "string[]",
        "supporting_evidence": "[{evidence_ref, finding}]",
        "recommended_actions": "string[]",
        "mission_need": "string?",
        "scope_summary": "string?",
        "key_services": "string[]",
        "deliverables": "string[]",
        "timeline": "string?",
        "risks": "string[]",
        "pursue_indicators": "string[]",
        "no_pursue_indicators": "string[]",
    }
    retrieval_query = (
        "mission scope deliverables timeline period of performance evaluation "
        "criteria risks staffing transition incumbent agency objectives"
    )
    retrieval_top_k = 12
    minimum_evidence = 1  # local dev with stub embeddings still produces output
