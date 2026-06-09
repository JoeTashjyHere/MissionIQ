"""Intelligence module + AI output schemas.

All module outputs share two contracts:

1. Every claim is backed by an ``evidence_ref`` (``E#`` for document chunks,
   ``M#`` for market intelligence). The platform validates these refs against
   retrieved evidence at persistence time.
2. Every downstream module (Compliance Matrix, Evaluation Criteria, Risk
   Register, …) is fed the latest **Customer DNA Profile** for the
   opportunity so its output is shaped by the customer's mission, strategic
   goals, success metrics, and stakeholder concerns — not by generic
   document extraction.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.common import Citation, ORMModel


class ModuleSpec(BaseModel):
    id: str
    group: str
    label: str
    description: str
    version: str
    output_schema_summary: dict[str, str]
    requires_customer_dna: bool = False
    consumes_company_profile: bool = False


class RunModuleRequest(BaseModel):
    force: bool = False
    model_override: str | None = None


class ModelMeta(BaseModel):
    provider: str
    name: str


class TokenMeta(BaseModel):
    input: int | None = None
    output: int | None = None


class AIOutputResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    module_id: str
    module_version: str
    status: Literal["ok", "insufficient_context", "error"]
    model_provider: str
    model_name: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    output_json: dict[str, Any]
    citations: list[Citation] = []
    generated_at: datetime


# ── Shared primitives ──


class SupportingEvidenceItem(BaseModel):
    """Single piece of supporting evidence as cited by the model.

    ``evidence_ref`` is the canonical pointer (e.g. ``E1`` or ``M2``) into the
    EVIDENCE block of the prompt.
    """

    evidence_ref: str
    finding: str


# ── Opportunity Summary ──


class OpportunitySummaryOutput(BaseModel):
    """Canonical four-section executive briefing."""

    executive_summary: str
    key_findings: list[str]
    supporting_evidence: list[SupportingEvidenceItem] = []
    recommended_actions: list[str]

    mission_need: str | None = None
    scope_summary: str | None = None
    key_services: list[str] = []
    deliverables: list[str] = []
    timeline: str | None = None
    risks: list[str] = []
    pursue_indicators: list[str] = []
    no_pursue_indicators: list[str] = []
    citations: list[dict] = []


# ── Customer DNA Profile ──
# The platform's central synthesis. Every downstream module reads this so
# their outputs are shaped by the customer, not by generic document extraction.


class CustomerDnaProfile(BaseModel):
    """Synthesis of who this customer is, what they care about, and how they
    measure success. Generated from documents + agency mission + agency
    strategic priorities + operating environment + evaluation criteria +
    contract context + market intelligence + customer profile.

    All downstream modules consume this profile. Its presence is the
    difference between extraction-grade output and consultant-grade output.
    """

    mission: str
    strategic_goals: list[str]
    core_values: list[str]
    success_metrics: list[str]
    operational_challenges: list[str]
    technology_priorities: list[str]
    risk_priorities: list[str]
    stakeholder_concerns: list[str]

    executive_summary: str
    key_findings: list[str] = []
    supporting_evidence: list[SupportingEvidenceItem] = []
    recommended_actions: list[str] = []

    confidence: Literal["high", "medium", "low", "insufficient"] = "medium"
    citations: list[dict] = []


# ── Compliance Matrix ──


class ComplianceRow(BaseModel):
    requirement_id: str
    requirement_text: str
    source_document: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    category: str | None = None
    response_owner: str | None = None
    proposed_status: Literal["open", "in_progress", "complete", "n_a"] = "open"
    notes: str | None = None

    # Insight-grade columns (the differentiators)
    why_requirement_exists: str
    mission_alignment: str
    customer_priority: Literal["critical", "high", "medium", "low"] = "medium"


class ComplianceMatrixOutput(BaseModel):
    executive_summary: str
    key_findings: list[str]
    supporting_evidence: list[SupportingEvidenceItem] = []
    recommended_actions: list[str]

    rows: list[ComplianceRow]
    coverage_gaps: list[str] = []
    citations: list[dict] = []


# ── Evaluation Criteria ──


class EvaluationFactor(BaseModel):
    factor: str
    subfactor: str | None = None
    importance: Literal[
        "most_important", "important", "less_important", "equal", "unspecified"
    ] = "unspecified"
    required_response_elements: list[str] = []
    source_section: str | None = None
    source_page: int | None = None


class EvaluationCriteriaOutput(BaseModel):
    executive_summary: str
    key_findings: list[str]
    supporting_evidence: list[SupportingEvidenceItem] = []
    recommended_actions: list[str]

    factors: list[EvaluationFactor]

    # Insight-grade fields (the differentiators)
    evaluation_intelligence: str
    likely_decision_drivers: list[str]
    potential_discriminators: list[str]
    potential_weaknesses: list[str]
    strategic_recommendations: list[str]

    citations: list[dict] = []


# ── Risk Register ──


class RiskItem(BaseModel):
    title: str
    description: str
    mission_impact: str
    probability: Literal["low", "medium", "high"] = "medium"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    mitigation: str
    supporting_evidence: list[str] = []
    owner: str | None = None


class RiskRegisterOutput(BaseModel):
    """Risks lanes are the canonical capture-management taxonomy.

    The four lanes force the model to think across the full pursuit lifecycle
    (winning, writing, executing, retaining) rather than dumping every risk
    into one bucket.
    """

    executive_summary: str
    key_findings: list[str]
    supporting_evidence: list[SupportingEvidenceItem] = []
    recommended_actions: list[str]

    capture_risks: list[RiskItem] = []
    proposal_risks: list[RiskItem] = []
    delivery_risks: list[RiskItem] = []
    customer_risks: list[RiskItem] = []

    top_risks: list[str] = []
    citations: list[dict] = []


# ── Company DNA Profile (seller-side synthesis) ──
# The mirror of Customer DNA. Where Customer DNA captures who the customer is,
# Company DNA captures who *we* are and how credibly we can win and deliver.


class CompanyDnaProfile(BaseModel):
    """Synthesis of the company pursuing the work, drawn from the workspace
    Company Profile + capability catalog.

    Downstream personalization (Capability Match, win themes, proof points)
    reads this so outputs are tailored to both sides of the deal.
    """

    company_summary: str
    core_capabilities: list[str]
    past_performance: list[str]
    contract_vehicles: list[str] = []
    certifications: list[str] = []
    technology_partners: list[str] = []
    differentiators: list[str]
    case_studies: list[str] = []
    key_personnel: list[str] = []
    geographic_footprint: str | None = None
    security_posture: str | None = None
    delivery_model: str | None = None
    pricing_posture: str | None = None

    executive_summary: str
    key_findings: list[str] = []
    recommended_actions: list[str] = []

    confidence: Literal["high", "medium", "low", "insufficient"] = "medium"
    profile_completeness: Literal["complete", "partial", "empty"] = "partial"


# ── Capability Match (seller × customer fit assessment) ──


class FitArea(BaseModel):
    """A single fit assessment with the rationale a capture lead would give."""

    area: str
    rationale: str
    evidence_refs: list[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"


class TeamingRecommendation(BaseModel):
    partner_profile: str
    fills_gap: str
    rationale: str


class CompanyGapRisk(BaseModel):
    title: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    mitigation: str


class CapabilityMatchOutput(BaseModel):
    """A senior-capture-lead assessment of whether we can credibly win and
    deliver: where we are strong, where we are weak, what is missing, and the
    concrete moves (proof points, teaming, discriminators, win themes,
    capture questions) that close the gap.
    """

    executive_summary: str
    win_assessment: str  # the candid "can we credibly win and deliver?" verdict
    fit_score: Literal["strong", "moderate", "marginal", "weak"] = "moderate"
    seller_data_complete: bool = True  # False ⇒ seller-side claims are assumptions

    strong_fit_areas: list[FitArea] = []
    weak_fit_areas: list[FitArea] = []
    missing_capabilities: list[str] = []
    required_proof_points: list[str] = []
    recommended_teaming_partners: list[TeamingRecommendation] = []
    suggested_discriminators: list[str] = []
    reusable_win_themes: list[str] = []
    capture_questions: list[str] = []
    proposal_risks: list[CompanyGapRisk] = []

    key_findings: list[str] = []
    recommended_actions: list[str] = []
    citations: list[dict] = []


# ── Win Strategy Engine (flagship synthesis) ──
# The culminating deliverable: a senior-capture-executive gate-review
# assessment that synthesizes Customer DNA, Company DNA, opportunity
# documents, evaluation criteria, Capability Match, market intelligence, and
# the Risk Register into strategic recommendations — NOT a document summary.
#
# Every point declares an epistemic basis so a gate review can tell apart
# what is proven from what is inferred from what is assumed.

StrategicBasis = Literal["evidence", "inference", "assumption"]


class StrategicPoint(BaseModel):
    """A single strategic conclusion with its evidentiary basis.

    ``sources`` cite the inputs that back the point, e.g.
    ``"Customer DNA: mission"``, ``"Company DNA: differentiators"``,
    ``"E2"`` (opportunity document evidence), ``"M1"`` (market intel).
    """

    statement: str
    basis: StrategicBasis = "inference"
    sources: list[str] = []


class BlackHatPoint(BaseModel):
    """A competitor's likely line of attack and our counter — the black-hat lens."""

    competitor_move: str
    impact: str
    our_counter: str
    basis: StrategicBasis = "inference"
    sources: list[str] = []


class CompetitorPosture(BaseModel):
    name: str  # e.g. "Incumbent (Acme)", "Large prime", "Niche small business"
    positioning: str
    threat_level: Literal["low", "medium", "high"] = "medium"
    our_response: str
    basis: StrategicBasis = "inference"
    sources: list[str] = []


class CompetitiveAssessment(BaseModel):
    summary: str
    competitors: list[CompetitorPosture] = []


class CaptureAction(BaseModel):
    action: str
    rationale: str
    priority: Literal["immediate", "near_term", "pre_rfp"] = "near_term"
    owner: str | None = None


class WinConfidenceAssessment(BaseModel):
    level: Literal["high", "medium", "low"] = "medium"
    score: int = 50  # 0–100 estimated probability of win
    rationale: str
    key_drivers: list[str] = []


class WinStrategyOutput(BaseModel):
    """A gate-review-grade pursuit assessment. Synthesis, not summary."""

    # 1. Executive Pursuit Recommendation
    executive_pursuit_recommendation: str
    pursuit_recommendation: Literal[
        "pursue", "pursue_with_conditions", "no_bid"
    ] = "pursue_with_conditions"

    # 2–7
    strengths: list[StrategicPoint] = []
    weaknesses: list[StrategicPoint] = []
    key_discriminators: list[StrategicPoint] = []
    black_hat_assessment: list[BlackHatPoint] = []
    likely_evaluator_concerns: list[StrategicPoint] = []
    win_themes: list[StrategicPoint] = []

    # 8. Competitive Assessment
    competitive_assessment: CompetitiveAssessment

    # 9. Critical Capture Actions
    critical_capture_actions: list[CaptureAction] = []

    # 10. Win Confidence Assessment
    win_confidence_assessment: WinConfidenceAssessment

    # Synthesis provenance: which upstream inputs were available
    inputs_used: list[str] = []
    inputs_missing: list[str] = []

    key_findings: list[str] = []
    citations: list[dict] = []
