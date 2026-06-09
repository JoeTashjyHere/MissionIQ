"""Capture: Compliance Matrix.

Consultant-grade requirements analysis. Every row includes why the
requirement exists, how it ladders into the Customer DNA mission, and
the customer's relative priority — not just a "shall" dump.

Requires Customer DNA Profile.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import ComplianceMatrixOutput


class ComplianceMatrixModule(BaseIntelligenceModule):
    id = "capture.compliance_matrix"
    group = "capture"
    label = "Compliance Matrix"
    description = (
        "Extract compliance requirements with consultant-grade analysis: why "
        "the requirement exists, how it aligns to the customer's mission, "
        "and the customer's relative priority. Consumes the Customer DNA "
        "Profile."
    )
    version = "v1"
    prompt_id = "capture.compliance_matrix"
    prompt_version = "v1"
    output_model = ComplianceMatrixOutput
    output_schema_summary = {
        "executive_summary": "string",
        "rows": (
            "[{requirement_id, requirement_text, source, category, "
            "why_requirement_exists, mission_alignment, customer_priority}]"
        ),
        "coverage_gaps": "string[]",
        "recommended_actions": "string[]",
    }
    retrieval_query = (
        "shall requirement Section L Section M PWS SOW compliance reporting "
        "security transition staffing past performance evaluation"
    )
    retrieval_top_k = 16
    minimum_evidence = 1
    requires_customer_dna = True
    consumes_company_profile = True
