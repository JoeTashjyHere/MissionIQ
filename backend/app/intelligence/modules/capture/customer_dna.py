"""Capture: Customer DNA Profile.

The platform's central synthesis step. Generates a portrait of the customer
across mission, strategic goals, values, success metrics, challenges,
technology priorities, risk priorities, and stakeholder concerns.

Every downstream Capture module (Compliance Matrix, Evaluation Criteria,
Risk Register, …) consumes the latest successful Customer DNA Profile so
their outputs are shaped by the customer rather than by generic AI
extraction.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import CustomerDnaProfile


class CustomerDnaModule(BaseIntelligenceModule):
    id = "capture.customer_dna"
    group = "capture"
    label = "Customer DNA Profile"
    description = (
        "Synthesize the customer behind this opportunity into a Customer DNA "
        "Profile: mission, strategic goals, core values, success metrics, "
        "operational challenges, technology priorities, risk priorities, and "
        "stakeholder concerns. Every downstream Capture module consumes this "
        "profile to produce consultant-grade output."
    )
    version = "v1"
    prompt_id = "capture.customer_dna"
    prompt_version = "v1"
    output_model = CustomerDnaProfile
    output_schema_summary = {
        "mission": "string",
        "strategic_goals": "string[]",
        "core_values": "string[]",
        "success_metrics": "string[]",
        "operational_challenges": "string[]",
        "technology_priorities": "string[]",
        "risk_priorities": "string[]",
        "stakeholder_concerns": "string[]",
        "executive_summary": "string",
        "key_findings": "string[]",
        "supporting_evidence": "[{evidence_ref, finding}]",
        "recommended_actions": "string[]",
        "confidence": "enum",
    }
    retrieval_query = (
        "agency mission strategic plan priorities operating environment "
        "stakeholders contracting officer program manager mission owner "
        "modernization technology priorities risk management oversight"
    )
    retrieval_top_k = 14
    minimum_evidence = 1
    requires_customer_dna = False  # This module IS the DNA producer
