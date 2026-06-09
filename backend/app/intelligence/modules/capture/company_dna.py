"""Capture: Company DNA Profile.

The seller-side mirror of Customer DNA. Synthesizes the workspace Company
Profile + capability catalog into an executive portrait of the company
pursuing the work, so downstream personalization (Capability Match, win
themes, proof points) is grounded in real seller-side data.

This module reads structured Company Profile data rather than opportunity
documents, so it does not require RAG evidence to produce output.
"""
from __future__ import annotations

from app.intelligence.base import BaseIntelligenceModule
from app.schemas.intelligence import CompanyDnaProfile


class CompanyDnaModule(BaseIntelligenceModule):
    id = "capture.company_dna"
    group = "capture"
    label = "Company DNA Profile"
    description = (
        "Synthesize the company pursuing the work into a Company DNA Profile: "
        "core capabilities, past performance, contract vehicles, "
        "certifications, technology partners, differentiators, case studies, "
        "key personnel, footprint, security posture, delivery model, and "
        "pricing posture. The seller-side mirror of the Customer DNA Profile."
    )
    version = "v1"
    prompt_id = "capture.company_dna"
    prompt_version = "v1"
    output_model = CompanyDnaProfile
    output_schema_summary = {
        "company_summary": "string",
        "core_capabilities": "string[]",
        "past_performance": "string[]",
        "contract_vehicles": "string[]",
        "certifications": "string[]",
        "technology_partners": "string[]",
        "differentiators": "string[]",
        "case_studies": "string[]",
        "key_personnel": "string[]",
        "delivery_model": "string?",
        "security_posture": "string?",
        "confidence": "enum",
        "profile_completeness": "enum",
    }
    retrieval_query = (
        "company capabilities past performance differentiators delivery model"
    )
    retrieval_top_k = 4
    # Company DNA is synthesized from the structured Company Profile, not from
    # opportunity documents — it must run even with zero RAG evidence.
    minimum_evidence = 0
    consumes_company_profile = True
    requires_customer_dna = False
