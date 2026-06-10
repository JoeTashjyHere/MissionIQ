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

from pydantic import BaseModel, Field

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


# ══════════════════════════════════════════════════════════════════════════
# Executive Briefings & Gate Reviews
# ══════════════════════════════════════════════════════════════════════════
# Leadership-facing deliverables that turn analysis into DECISIONS. These
# modules synthesize every upstream intelligence output (Customer DNA, Company
# DNA, Capability Match, Evaluation Intelligence, Risk Intelligence, Win
# Strategy, Market Intelligence, Pursuit Memory) into boardroom-ready packages.
#
# Two epistemic systems run side by side:
#   • Every analytic statement is tagged Evidence / Inference / Assumption.
#   • Recalled institutional knowledge is surfaced as HISTORICAL EVIDENCE.


class Confidence(BaseModel):
    level: Literal["high", "medium", "low"] = "medium"
    score: int = 50  # 0–100
    rationale: str = ""


class HistoricalEvidence(BaseModel):
    """Institutional knowledge recalled from Pursuit Memory. Every item here is
    HISTORICAL EVIDENCE — proven on prior pursuits, distinct from the current
    opportunity's evidence."""

    similar_opportunities: list[str] = []
    historical_win_themes: list[str] = []
    historical_risks: list[str] = []
    historical_discriminators: list[str] = []
    agency_patterns: list[str] = []


# ── Executive Brief (capture.executive_brief) ──


class OpportunitySnapshot(BaseModel):
    agency: str | None = None
    program: str | None = None
    estimated_value: str | None = None
    contract_vehicle: str | None = None
    due_date: str | None = None
    incumbent: str | None = None
    pursuit_status: str | None = None
    win_confidence: int = 50


class CustomerIntelligence(BaseModel):
    strategic_priorities: list[str] = []
    success_metrics: list[str] = []
    stakeholder_concerns: list[str] = []
    mission_drivers: list[str] = []


class CompanyPosition(BaseModel):
    strengths: list[StrategicPoint] = []
    gaps: list[StrategicPoint] = []
    proof_points: list[StrategicPoint] = []
    competitive_advantages: list[StrategicPoint] = []


class BriefWinStrategy(BaseModel):
    recommended_discriminators: list[StrategicPoint] = []
    key_themes: list[StrategicPoint] = []
    evaluation_priorities: list[StrategicPoint] = []
    critical_actions: list[CaptureAction] = []


class BriefRisk(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    mitigation: str | None = None
    basis: StrategicBasis = "inference"
    sources: list[str] = []


class BriefRisks(BaseModel):
    top_capture_risks: list[BriefRisk] = []
    top_proposal_risks: list[BriefRisk] = []
    top_delivery_risks: list[BriefRisk] = []


class ExecRecommendation(BaseModel):
    recommendation: Literal[
        "pursue_aggressively", "pursue_with_conditions", "monitor", "no_bid"
    ] = "pursue_with_conditions"
    confidence_level: Literal["high", "medium", "low"] = "medium"
    confidence_score: int = 50
    rationale: str = ""
    required_conditions: list[str] = []


class ExecutiveBriefOutput(BaseModel):
    """A one-screen, boardroom-ready executive brief. Section-modular so it can
    later map cleanly to slides for PowerPoint / PDF / Word export."""

    headline: str = ""
    opportunity_snapshot: OpportunitySnapshot
    customer_intelligence: CustomerIntelligence
    company_position: CompanyPosition
    win_strategy: BriefWinStrategy
    risks: BriefRisks
    executive_recommendation: ExecRecommendation
    historical_evidence: HistoricalEvidence = Field(default_factory=HistoricalEvidence)
    inputs_used: list[str] = []
    inputs_missing: list[str] = []
    key_findings: list[str] = []
    citations: list[dict] = []


# ── Gate Review (capture.gate_review) ──


class ScoreBlock(BaseModel):
    score: int = 50  # 0–100
    rationale: str = ""
    basis: StrategicBasis = "inference"
    drivers: list[str] = []
    sources: list[str] = []


class GateReviewOutput(BaseModel):
    """A formal bid/no-bid gate-review package — consulting-grade scoring plus
    the reasons, actions, questions, and escalations a board needs to decide."""

    headline: str = ""
    attractiveness_score: ScoreBlock
    competitive_position_score: ScoreBlock
    capability_alignment_score: ScoreBlock
    # Higher risk_score == MORE risk (worse). The rationale states the drivers.
    risk_score: ScoreBlock
    probability_of_win: Confidence
    top_reasons_to_pursue: list[StrategicPoint] = []
    top_reasons_not_to_pursue: list[StrategicPoint] = []
    decision_recommendation: Literal[
        "pursue", "pursue_with_conditions", "no_bid"
    ] = "pursue_with_conditions"
    decision_summary: str = ""
    required_executive_actions: list[CaptureAction] = []
    open_questions: list[str] = []
    escalations: list[str] = []
    historical_evidence: HistoricalEvidence = Field(default_factory=HistoricalEvidence)
    inputs_used: list[str] = []
    inputs_missing: list[str] = []
    key_findings: list[str] = []
    citations: list[dict] = []


# ── Bid / No-Bid Decision (capture.bid_decision) ──


class DecisionFactor(BaseModel):
    name: str
    score: int = 50  # 0–100
    rationale: str = ""
    evidence: list[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"
    basis: StrategicBasis = "inference"


class BidDecisionOutput(BaseModel):
    """A focused executive bid/no-bid recommendation scored across the six
    canonical decision factors."""

    recommendation: Literal["bid", "conditional_bid", "no_bid"] = "conditional_bid"
    executive_summary: str = ""
    confidence: Confidence
    factors: list[DecisionFactor] = []
    decision_drivers: list[str] = []
    required_next_steps: list[CaptureAction] = []
    historical_evidence: HistoricalEvidence = Field(default_factory=HistoricalEvidence)
    inputs_used: list[str] = []
    inputs_missing: list[str] = []
    citations: list[dict] = []


# ── Outcome Intelligence (capture.outcome_intelligence) ──


class OutcomeIntelligenceOutput(BaseModel):
    """What the organization's win/loss track record means for THIS pursuit.

    Hard epistemic rule: track records are observed patterns and historical
    correlations. The module reports what was observed and what it implies as
    clearly-labeled inference — it never claims a pattern *caused* a win or
    loss.
    """

    outcome_context_summary: str = ""
    relevant_win_patterns: list[StrategicPoint] = []
    relevant_loss_patterns: list[StrategicPoint] = []
    agency_track_record: list[StrategicPoint] = []
    competitor_track_record: list[StrategicPoint] = []
    strategic_recommendations: list[CaptureAction] = []
    confidence: Confidence
    historical_evidence: HistoricalEvidence = Field(default_factory=HistoricalEvidence)
    inputs_used: list[str] = []
    inputs_missing: list[str] = []
    citations: list[dict] = []
