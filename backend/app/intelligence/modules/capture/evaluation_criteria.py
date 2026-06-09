"""Capture: Evaluation Criteria.

Section M decomposition PLUS evaluation intelligence: decision drivers,
discriminators, weaknesses, strategic recommendations. Requires Customer
DNA Profile.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import EvaluationCriteriaOutput


class EvaluationCriteriaModule(BaseIntelligenceModule):
    id = "capture.evaluation_criteria"
    group = "capture"
    label = "Evaluation Criteria"
    description = (
        "Decompose Section M and produce capture-grade evaluation intelligence: "
        "decision drivers, discriminators, weaknesses, and strategic "
        "recommendations — informed by the Customer DNA Profile."
    )
    version = "v1"
    prompt_id = "capture.evaluation_criteria"
    prompt_version = "v1"
    output_model = EvaluationCriteriaOutput
    output_schema_summary = {
        "factors": "[{factor, subfactor, importance, required_response_elements}]",
        "evaluation_intelligence": "string",
        "likely_decision_drivers": "string[]",
        "potential_discriminators": "string[]",
        "potential_weaknesses": "string[]",
        "strategic_recommendations": "string[]",
    }
    retrieval_query = (
        "Section M evaluation factors subfactor best value trade-off LPTA "
        "most important importance award criteria past performance technical"
    )
    retrieval_top_k = 14
    minimum_evidence = 1
    requires_customer_dna = True
