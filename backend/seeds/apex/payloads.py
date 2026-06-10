"""Schema-valid intelligence payloads for Apex Federal demo pursuits."""
from __future__ import annotations

from typing import Any

from seeds.apex.constants import PursuitSpec


def _pt(statement: str, basis: str = "evidence") -> dict[str, Any]:
    return {"statement": statement, "basis": basis, "sources": ["Customer DNA", "E1"]}


def customer_dna(p: PursuitSpec) -> dict[str, Any]:
    return {
        "mission": (
            f"{p.agency} seeks to modernize {p.name.lower()} with measurable "
            "citizen and workforce outcomes."
        ),
        "strategic_goals": p.themes + ["Operational excellence", "Cost efficiency"],
        "core_values": ["Transparency", "Mission service", "Accountability"],
        "success_metrics": ["CSAT ≥ 4.2", "AHT reduction 15%", "Self-service deflection 30%"],
        "operational_challenges": [
            "Legacy platform constraints",
            "Workforce skill gaps",
            "Rising contact volume",
        ],
        "technology_priorities": ["Cloud", "AI automation", "CRM modernization"],
        "risk_priorities": ["Transition disruption", "Data migration", "Staffing continuity"],
        "stakeholder_concerns": [
            "Program continuity during transition",
            "Measurable CX improvement in year one",
        ],
        "executive_summary": (
            f"{p.agency} is prioritizing {p.themes[0].lower()} as the primary "
            f"differentiator for {p.name}. Evaluators will weight transition "
            "credibility and proven federal CX delivery."
        ),
        "key_findings": [f"Primary evaluation focus: {p.themes[0]}", "Incumbent pressure likely"],
        "confidence": "high",
        "citations": [{"ref": "E1", "claim": "Mission and scope from solicitation"}],
    }


def company_dna() -> dict[str, Any]:
    return {
        "company_summary": (
            "Apex Federal Solutions delivers contact center, citizen experience, "
            "and digital service operations for federal agencies."
        ),
        "core_capabilities": [
            "Contact Center Operations",
            "Citizen Experience",
            "Service Desk Management",
            "Salesforce Implementations",
            "AWS Cloud Services",
            "AI Automation",
        ],
        "past_performance": [
            "CMS Citizen Engagement Modernization (prime)",
            "VBA Benefits Experience Platform (prime)",
            "FCSA Digital Experience Transformation (sub)",
        ],
        "contract_vehicles": ["GSA MAS", "OASIS+", "CIO-SP4", "8(a) STARS III"],
        "technology_partners": ["Salesforce", "AWS", "ServiceNow", "Microsoft", "Genesys"],
        "differentiators": [
            "Omnichannel CX at federal scale",
            "Zero-disruption transition methodology",
            "AI-enabled self-service with human escalation",
        ],
        "executive_summary": (
            "Apex brings mature contact center and CX credentials with platform "
            "partnerships across Salesforce, ServiceNow, and AWS."
        ),
        "confidence": "high",
        "profile_completeness": "complete",
        "key_findings": ["Strong CX portfolio", "Proven transition track record"],
    }


def compliance_matrix(p: PursuitSpec) -> dict[str, Any]:
    return {
        "executive_summary": f"Compliance posture for {p.name} is manageable with standard federal artifacts.",
        "key_findings": ["Section L/M requirements mapped"],
        "recommended_actions": ["Finalize compliance matrix owners"],
        "rows": [
            {
                "requirement_id": "R-001",
                "requirement_text": "Submit technical and management volumes per Section L.",
                "category": "Instructions",
                "why_requirement_exists": "Ensures evaluators receive comparable proposals.",
                "mission_alignment": "Supports structured evaluation of CX approach.",
                "customer_priority": "critical",
            }
        ],
        "citations": [],
    }


def evaluation_criteria(p: PursuitSpec) -> dict[str, Any]:
    return {
        "executive_summary": f"Technical approach and past performance dominate scoring for {p.name}.",
        "key_findings": [f"Primary discriminator: {p.themes[0]}"],
        "recommended_actions": ["Align win themes to Factor 1"],
        "factors": [
            {
                "factor": "Technical/Management Approach",
                "importance": "most_important",
                "required_response_elements": [p.themes[0], "Transition plan", "Staffing model"],
            },
            {
                "factor": "Past Performance",
                "importance": "important",
                "required_response_elements": ["Relevant federal CX contracts"],
            },
        ],
        "evaluation_intelligence": "Approach and transition together outweigh price.",
        "likely_decision_drivers": [p.themes[0], "Transition credibility"],
        "potential_discriminators": ["AI-enabled self-service", "Zero-disruption transition"],
        "potential_weaknesses": ["Incumbent familiarity"] if p.incumbent else [],
        "strategic_recommendations": ["Lead with proven transition narrative"],
        "citations": [],
    }


def risk_register(p: PursuitSpec) -> dict[str, Any]:
    risk = {
        "title": "Transition service disruption",
        "description": "Knowledge transfer gaps during phase-in.",
        "mission_impact": "Citizen wait times could spike during cutover.",
        "probability": "medium",
        "severity": "high",
        "mitigation": "Parallel operations with hypercare stabilization window.",
    }
    return {
        "executive_summary": f"Capture risks for {p.name} are manageable with proactive mitigation.",
        "key_findings": ["Transition is the highest-weight risk"],
        "recommended_actions": ["Stand up transition cell pre-award"],
        "capture_risks": [risk],
        "proposal_risks": [risk],
        "delivery_risks": [],
        "customer_risks": [],
        "top_risks": ["Transition service disruption"],
        "citations": [],
    }


def capability_match(p: PursuitSpec) -> dict[str, Any]:
    fit = "strong" if p.outcome != "no_bid" else "marginal"
    return {
        "executive_summary": (
            f"Apex {'aligns strongly' if fit == 'strong' else 'has gaps'} with "
            f"{p.name} requirements."
        ),
        "win_assessment": (
            "Credible win with proven CX credentials."
            if fit == "strong"
            else "Strategic misalignment — limited proof points for this mission."
        ),
        "fit_score": fit,
        "seller_data_complete": True,
        "strong_fit_areas": [
            {"area": p.themes[0], "rationale": "Core Apex capability with federal references."}
        ],
        "weak_fit_areas": [],
        "missing_capabilities": [] if fit == "strong" else ["Classified operations support"],
        "required_proof_points": [f"Federal {p.themes[0]} case study"],
        "suggested_discriminators": ["Zero-disruption transition", "AI-enabled self-service"],
        "reusable_win_themes": p.themes,
        "capture_questions": ["What is the agency's target self-service deflection rate?"],
        "proposal_risks": [],
        "key_findings": [f"Fit score: {fit}"],
        "recommended_actions": ["Validate proof points with program office"],
        "citations": [],
    }


def win_strategy(p: PursuitSpec) -> dict[str, Any]:
    rec = "no_bid" if p.outcome == "no_bid" else "pursue_with_conditions"
    if p.outcome == "won":
        rec = "pursue"
    score = 72 if p.outcome == "won" else 58 if p.outcome is None else 35
    if p.outcome == "lost":
        score = 42
    return {
        "executive_pursuit_recommendation": (
            f"{'Pursue' if rec != 'no_bid' else 'No-bid'} — {p.name} at {p.agency}."
        ),
        "pursuit_recommendation": rec,
        "strengths": [_pt(f"Strong fit in {p.themes[0]}")],
        "weaknesses": [_pt("Incumbent relationship pressure", "inference")] if p.incumbent else [],
        "key_discriminators": [_pt("Zero-disruption transition methodology")],
        "black_hat_assessment": [
            {
                "competitor_move": f"{p.incumbent or 'Competitor'} emphasizes continuity.",
                "impact": "Evaluators may default to incumbent familiarity.",
                "our_counter": "Lead with quantified transition outcomes from CMS and VBA.",
                "basis": "inference",
                "sources": ["Historical Proposal Evidence"],
            }
        ],
        "likely_evaluator_concerns": [_pt("Transition risk during phase-in")],
        "win_themes": [_pt(t) for t in p.themes[:2]],
        "competitive_assessment": {
            "summary": f"Competitive field includes {p.incumbent or 'multiple primes'}.",
            "competitors": [
                {
                    "name": p.incumbent or "Regional prime",
                    "positioning": "Incumbent continuity narrative",
                    "threat_level": "high" if p.incumbent else "medium",
                    "our_response": "Historical evidence of zero-disruption transitions.",
                    "basis": "evidence",
                    "sources": ["Proposal Repository"],
                }
            ],
        },
        "critical_capture_actions": [
            {
                "action": "Validate transition SMEs with program office",
                "rationale": "Transition is the primary evaluation factor.",
                "priority": "immediate",
            }
        ],
        "win_confidence_assessment": {
            "level": "high" if score >= 70 else "medium" if score >= 50 else "low",
            "score": score,
            "rationale": "Based on fit, competition, and historical patterns.",
            "key_drivers": p.themes[:2],
        },
        "inputs_used": ["Customer DNA", "Company DNA", "Capability Match"],
        "inputs_missing": [],
        "key_findings": [f"Recommendation: {rec}"],
        "citations": [],
    }


def executive_brief(p: PursuitSpec) -> dict[str, Any]:
    ws = win_strategy(p)
    score = ws["win_confidence_assessment"]["score"]
    return {
        "headline": f"{p.agency}: {p.name} — {'strong pursuit' if score >= 60 else 'caution'}",
        "opportunity_snapshot": {
            "agency": p.agency,
            "program": p.name,
            "estimated_value": f"${p.value_cents / 100_000_000:.0f}M",
            "contract_vehicle": p.contract_vehicle,
            "incumbent": p.incumbent,
            "pursuit_status": p.capture_stage,
            "win_confidence": score,
        },
        "customer_intelligence": {
            "strategic_priorities": p.themes,
            "success_metrics": ["CSAT improvement", "Cost per contact reduction"],
            "stakeholder_concerns": ["Transition continuity"],
            "mission_drivers": [p.themes[0]],
        },
        "company_position": {
            "strengths": [_pt("Federal CX at scale")],
            "gaps": [],
            "proof_points": [_pt("CMS and VBA past performance")],
            "competitive_advantages": [_pt("Zero-disruption transition")],
        },
        "win_strategy": {
            "recommended_discriminators": [_pt("AI-enabled self-service")],
            "key_themes": [_pt(t) for t in p.themes[:2]],
            "evaluation_priorities": [_pt("Technical approach")],
            "critical_actions": ws["critical_capture_actions"],
        },
        "risks": {
            "top_capture_risks": [
                {
                    "title": "Transition disruption",
                    "severity": "high",
                    "mitigation": "Parallel operations plan",
                    "basis": "evidence",
                }
            ],
            "top_proposal_risks": [],
            "top_delivery_risks": [],
        },
        "executive_recommendation": {
            "recommendation": "pursue_with_conditions" if score >= 55 else "monitor",
            "confidence_level": "medium",
            "confidence_score": score,
            "rationale": ws["executive_pursuit_recommendation"],
            "required_conditions": ["Transition SME validation"],
        },
        "historical_evidence": {
            "historical_win_themes": ["Zero-disruption transition", "Omnichannel CX"],
            "agency_patterns": [f"{p.agency}: transition narratives correlate with wins"],
        },
        "inputs_used": ["Win Strategy", "Customer DNA"],
        "key_findings": [ws["executive_pursuit_recommendation"]],
        "citations": [],
    }


def gate_review(p: PursuitSpec) -> dict[str, Any]:
    ws = win_strategy(p)
    score = ws["win_confidence_assessment"]["score"]
    block = lambda s, r: {"score": s, "rationale": r, "basis": "inference", "drivers": [], "sources": []}
    return {
        "headline": f"Gate Review: {p.name}",
        "attractiveness_score": block(min(score + 5, 95), "Strong market fit and vehicle access."),
        "competitive_position_score": block(score, "Incumbent pressure moderates position."),
        "capability_alignment_score": block(score + 8, "Core capabilities align with requirements."),
        "risk_score": block(max(100 - score, 25), "Transition risk is primary concern."),
        "probability_of_win": {
            "level": ws["win_confidence_assessment"]["level"],
            "score": score,
            "rationale": ws["win_confidence_assessment"]["rationale"],
        },
        "top_reasons_to_pursue": [_pt(f"Strong {p.themes[0]} credentials")],
        "top_reasons_not_to_pursue": [_pt("Incumbent advantage", "inference")] if p.incumbent else [],
        "decision_recommendation": ws["pursuit_recommendation"],
        "decision_summary": ws["executive_pursuit_recommendation"],
        "required_executive_actions": ws["critical_capture_actions"],
        "open_questions": ["Confirm evaluation factor weighting"],
        "escalations": [],
        "historical_evidence": {"historical_win_themes": ["Zero-disruption transition"]},
        "inputs_used": ["Win Strategy"],
        "key_findings": [],
        "citations": [],
    }


def bid_decision(p: PursuitSpec) -> dict[str, Any]:
    ws = win_strategy(p)
    rec = "no_bid" if ws["pursuit_recommendation"] == "no_bid" else "conditional_bid"
    if p.outcome == "won":
        rec = "bid"
    return {
        "recommendation": rec,
        "executive_summary": ws["executive_pursuit_recommendation"],
        "confidence": {
            "level": ws["win_confidence_assessment"]["level"],
            "score": ws["win_confidence_assessment"]["score"],
            "rationale": "Synthesis of fit, competition, and risk.",
        },
        "factors": [
            {
                "name": "Strategic Fit",
                "score": ws["win_confidence_assessment"]["score"],
                "rationale": p.themes[0],
                "basis": "evidence",
            }
        ],
        "decision_drivers": p.themes[:2],
        "required_next_steps": ws["critical_capture_actions"],
        "historical_evidence": {},
        "inputs_used": ["Gate Review", "Win Strategy"],
        "citations": [],
    }


def outcome_intelligence(p: PursuitSpec) -> dict[str, Any]:
    return {
        "outcome_context_summary": (
            f"Apex's track record shows recurring success with transition-heavy "
            f"CX pursuits like {p.name}."
        ),
        "relevant_win_patterns": [
            {
                "statement": "Zero-disruption transition appeared in multiple won pursuits.",
                "basis": "evidence",
                "sources": ["Outcome Intelligence", "Proposal Repository"],
            }
        ],
        "relevant_loss_patterns": [],
        "agency_track_record": [
            {
                "statement": f"Observed patterns for {p.agency} — historical correlation only.",
                "basis": "evidence",
                "sources": ["Outcome Intelligence"],
            }
        ],
        "competitor_track_record": [],
        "strategic_recommendations": [
            {
                "action": "Reuse CMS transition narrative as Historical Evidence.",
                "rationale": "Observed pattern in prior wins.",
                "priority": "near_term",
            }
        ],
        "confidence": {"level": "medium", "score": 65, "rationale": "42 pursuits recorded."},
        "historical_evidence": {"historical_win_themes": p.themes},
        "inputs_used": ["Outcome context"],
        "inputs_missing": [],
        "citations": [],
    }


MODULE_BUILDERS: dict[str, Any] = {
    "capture.customer_dna": customer_dna,
    "capture.company_dna": lambda p: company_dna(),
    "capture.compliance_matrix": compliance_matrix,
    "capture.evaluation_criteria": evaluation_criteria,
    "capture.risk_register": risk_register,
    "capture.capability_match": capability_match,
    "capture.win_strategy": win_strategy,
    "capture.executive_brief": executive_brief,
    "capture.gate_review": gate_review,
    "capture.bid_decision": bid_decision,
    "capture.outcome_intelligence": outcome_intelligence,
}


def build_payload(module_id: str, pursuit: PursuitSpec) -> dict[str, Any]:
    builder = MODULE_BUILDERS[module_id]
    return builder(pursuit)
