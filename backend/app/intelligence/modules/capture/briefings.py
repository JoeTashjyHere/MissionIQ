"""Capture: Executive Briefings & Gate Reviews.

These are MissionIQ's leadership-facing deliverables. They do NOT summarize
documents — they synthesize every upstream intelligence output into a decision
package a Growth VP, Capture Director, or Managing Director can act on in under
a minute:

- ``capture.executive_brief`` — the one-screen executive brief.
- ``capture.gate_review``     — the formal bid/no-bid gate-review package.
- ``capture.bid_decision``    — the focused bid / no-bid recommendation.

All three consume the same intelligence layer (Customer DNA, Company DNA,
Capability Match, Evaluation Intelligence, Risk Intelligence, Win Strategy,
market intelligence, and Pursuit Memory). Each upstream input is optional
except the Customer DNA Profile; missing inputs are recorded and confidence is
dampened rather than fabricated.
"""
from __future__ import annotations

from typing import Any

from app.intelligence.base import BaseIntelligenceModule, RAGContext
from app.schemas.intelligence import (
    BidDecisionOutput,
    ExecutiveBriefOutput,
    GateReviewOutput,
)


class _BriefingModule(BaseIntelligenceModule):
    """Shared wiring for the briefing modules: require Customer DNA, consume the
    Company Profile and Pursuit Memory, and load every upstream synthesis
    output the briefing reasons over."""

    group = "capture"
    retrieval_top_k = 14
    minimum_evidence = 1
    requires_customer_dna = True
    consumes_company_profile = True
    consumes_memory = True
    consumes_proposal_repository = True

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        async def latest(module_id: str) -> dict[str, Any] | None:
            return await self._load_latest_output(
                workspace_id=ctx.workspace_id,
                opportunity_id=ctx.opportunity_id,
                module_id=module_id,
            )

        return {
            "company_dna": await latest("capture.company_dna"),
            "capability_match": await latest("capture.capability_match"),
            "evaluation_criteria": await latest("capture.evaluation_criteria"),
            "risk_register": await latest("capture.risk_register"),
            "win_strategy": await latest("capture.win_strategy"),
        }


class ExecutiveBriefModule(_BriefingModule):
    id = "capture.executive_brief"
    label = "Executive Brief"
    description = (
        "The primary executive-facing deliverable. Synthesizes all MissionIQ "
        "intelligence into a one-screen leadership brief: opportunity snapshot, "
        "customer intelligence, company position, win strategy, risks, and an "
        "executive recommendation (pursue aggressively / with conditions / "
        "monitor / no-bid). Every statement is tagged Evidence, Inference, or "
        "Assumption; recalled prior intelligence is labeled Historical Evidence."
    )
    version = "v1"
    prompt_id = "capture.executive_brief"
    prompt_version = "v1"
    output_model = ExecutiveBriefOutput
    output_schema_summary = {
        "headline": "string",
        "opportunity_snapshot": "{agency, program, estimated_value, ...}",
        "customer_intelligence": "{strategic_priorities[], success_metrics[], ...}",
        "company_position": "{strengths[], gaps[], proof_points[], advantages[]}",
        "win_strategy": "{discriminators[], themes[], priorities[], actions[]}",
        "risks": "{capture[], proposal[], delivery[]}",
        "executive_recommendation": "{recommendation, confidence, conditions[]}",
        "historical_evidence": "{similar_opps[], win_themes[], risks[], ...}",
    }
    retrieval_query = (
        "mission objectives evaluation factors discriminators incumbent "
        "competition past performance risk transition win themes value due date"
    )


class GateReviewModule(_BriefingModule):
    id = "capture.gate_review"
    label = "Gate Review"
    description = (
        "A formal bid/no-bid gate-review package. Scores Opportunity "
        "Attractiveness, Competitive Position, Capability Alignment, and Risk; "
        "assesses Probability of Win; and lays out top reasons to pursue / not "
        "pursue, the decision recommendation, required executive actions, open "
        "questions, and escalations — the way a consulting gate review reads."
    )
    version = "v1"
    prompt_id = "capture.gate_review"
    prompt_version = "v1"
    output_model = GateReviewOutput
    output_schema_summary = {
        "attractiveness_score": "{score, rationale, basis, drivers[]}",
        "competitive_position_score": "{score, ...}",
        "capability_alignment_score": "{score, ...}",
        "risk_score": "{score, ...}",
        "probability_of_win": "{level, score, rationale}",
        "top_reasons_to_pursue": "[{statement, basis, sources}]",
        "top_reasons_not_to_pursue": "[{statement, basis, sources}]",
        "decision_recommendation": "enum",
        "required_executive_actions": "[{action, priority, rationale}]",
        "open_questions": "string[]",
        "escalations": "string[]",
    }
    retrieval_query = (
        "evaluation factors competition incumbent past performance risk budget "
        "set aside contract vehicle timeline win probability attractiveness"
    )


class BidDecisionModule(_BriefingModule):
    id = "capture.bid_decision"
    label = "Bid / No-Bid Decision"
    description = (
        "A focused executive bid/no-bid recommendation. Scores the six decision "
        "factors — Strategic Alignment, Revenue Potential, Relationship "
        "Position, Competitive Position, Delivery Readiness, Risk Profile — each "
        "with rationale, evidence, and confidence, then returns Bid / "
        "Conditional Bid / No-Bid with decision drivers and required next steps."
    )
    version = "v1"
    prompt_id = "capture.bid_decision"
    prompt_version = "v1"
    output_model = BidDecisionOutput
    output_schema_summary = {
        "recommendation": "bid | conditional_bid | no_bid",
        "executive_summary": "string",
        "confidence": "{level, score, rationale}",
        "factors": "[{name, score, rationale, evidence[], confidence, basis}]",
        "decision_drivers": "string[]",
        "required_next_steps": "[{action, priority, rationale}]",
    }
    retrieval_query = (
        "strategic alignment revenue relationship competition delivery readiness "
        "risk incumbent past performance budget value win probability"
    )
