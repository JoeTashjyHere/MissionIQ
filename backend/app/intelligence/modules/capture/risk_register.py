"""Capture: Risk Register.

Categorized risk analysis across the four canonical capture lanes (Capture,
Proposal, Delivery, Customer). Every risk carries mission impact,
probability, severity, mitigation, and supporting evidence. Requires
Customer DNA Profile.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import RiskRegisterOutput


class RiskRegisterModule(BaseIntelligenceModule):
    id = "capture.risk_register"
    group = "capture"
    label = "Risk Register"
    description = (
        "Identify risks across Capture, Proposal, Delivery, and Customer "
        "lanes. Each risk carries mission impact, probability, severity, "
        "mitigation, and supporting evidence — weighted against the "
        "Customer DNA Profile."
    )
    version = "v1"
    prompt_id = "capture.risk_register"
    prompt_version = "v1"
    output_model = RiskRegisterOutput
    output_schema_summary = {
        "capture_risks": "[risk]",
        "proposal_risks": "[risk]",
        "delivery_risks": "[risk]",
        "customer_risks": "[risk]",
        "top_risks": "string[]",
        "risk": (
            "{title, description, mission_impact, probability, severity, "
            "mitigation, supporting_evidence, owner}"
        ),
    }
    retrieval_query = (
        "risk transition incumbent staffing clearance fedramp security "
        "schedule deliverable past performance subcontractor mission "
        "continuity oversight"
    )
    retrieval_top_k = 16
    minimum_evidence = 1
    requires_customer_dna = True
    consumes_company_profile = True
