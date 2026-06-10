"""Apex Federal Solutions — synthetic demo workspace constants.

All organizations, agencies, and pursuits are fictional. No real customers,
competitors, or proprietary content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEMO_PASSWORD = "MissionIQ!Demo2026"
WORKSPACE_SLUG = "apex-federal"
WORKSPACE_NAME = "Apex Federal Solutions"

DEMO_USERS: list[dict[str, str]] = [
    {
        "email": "sarah.mitchell@apexfederal.demo",
        "full_name": "Sarah Mitchell",
        "title": "Vice President, Growth",
        "role": "administrator",
    },
    {
        "email": "michael.reynolds@apexfederal.demo",
        "full_name": "Michael Reynolds",
        "title": "Capture Director",
        "role": "approver",
    },
    {
        "email": "jennifer.carter@apexfederal.demo",
        "full_name": "Jennifer Carter",
        "title": "Proposal Manager",
        "role": "reviewer",
    },
    {
        "email": "david.kim@apexfederal.demo",
        "full_name": "David Kim",
        "title": "Capture Analyst",
        "role": "contributor",
    },
    {
        "email": "emily.turner@apexfederal.demo",
        "full_name": "Emily Turner",
        "title": "Business Development Associate",
        "role": "viewer",
    },
]

CAPABILITIES: list[dict[str, Any]] = [
    {
        "name": "Contact Center Operations",
        "category": "Operations",
        "maturity": "mature",
        "description": "Omnichannel contact center design, staffing, and 24x7 operations.",
        "keywords": ["contact center", "citizen experience", "omnichannel"],
    },
    {
        "name": "Citizen Experience",
        "category": "CX",
        "maturity": "mature",
        "description": "Journey mapping, service design, and CX measurement for federal programs.",
        "keywords": ["cx", "journey", "citizen"],
    },
    {
        "name": "Service Desk Management",
        "category": "Operations",
        "maturity": "mature",
        "description": "ITIL-aligned service desk, tiered support, and knowledge management.",
        "keywords": ["service desk", "itil", "tier 1"],
    },
    {
        "name": "Salesforce Implementations",
        "category": "Technology",
        "maturity": "mature",
        "description": "Salesforce Service Cloud, Experience Cloud, and case management.",
        "keywords": ["salesforce", "service cloud"],
    },
    {
        "name": "ServiceNow Implementations",
        "category": "Technology",
        "maturity": "mature",
        "description": "ITSM, CSM, and workflow automation on the ServiceNow platform.",
        "keywords": ["servicenow", "itsm"],
    },
    {
        "name": "AWS Cloud Services",
        "category": "Technology",
        "maturity": "mature",
        "description": "FedRAMP-aligned cloud migration, landing zones, and managed services.",
        "keywords": ["aws", "cloud", "fedramp"],
    },
    {
        "name": "Workforce Modernization",
        "category": "Transformation",
        "maturity": "developing",
        "description": "Staffing model redesign, skills-based routing, and change management.",
        "keywords": ["workforce", "modernization"],
    },
    {
        "name": "AI Automation",
        "category": "Technology",
        "maturity": "developing",
        "description": "Virtual agents, intelligent routing, and agent-assist copilots.",
        "keywords": ["ai", "automation", "virtual agent"],
    },
]

COMPANY_PROFILE: dict[str, Any] = {
    "legal_name": "Apex Federal Solutions LLC",
    "primary_naics": "541512",
    "size_standard": "Small Business",
    "certifications": ["8(a)", "HUBZone", "ISO 9001"],
    "overview": (
        "Apex Federal Solutions is a mid-sized federal technology and operations "
        "contractor specializing in contact centers, citizen experience, service "
        "desk operations, AI enablement, cloud modernization, workforce "
        "transformation, and digital service delivery."
    ),
    "differentiators": (
        "Omnichannel CX at scale, AI-enabled self-service with human-in-the-loop "
        "escalation, and a proven zero-disruption transition methodology across "
        "15+ federal program transitions."
    ),
    "past_performance_summary": (
        "CMS citizen engagement, VBA benefits experience, FCSA digital services, "
        "and multiple service desk transformations — 12 prime contracts active."
    ),
    "contract_vehicles": ["GSA MAS", "OASIS+", "CIO-SP4", "8(a) STARS III"],
    "technology_partners": ["Salesforce", "AWS", "ServiceNow", "Microsoft", "Genesys"],
    "case_studies": (
        "Modernized a 2,400-seat contact center for a health agency with 34% "
        "self-service deflection in year one. Delivered a FedRAMP Moderate "
        "Salesforce Service Cloud deployment for a benefits program in nine months."
    ),
    "key_personnel": (
        "Program Director (PMP, 18 yrs federal CX), Transition Lead (ITIL Expert), "
        "Salesforce Practice Lead (5x certified), AI Practice Lead (former agency CIO advisor)."
    ),
    "geographic_footprint": "Washington DC; Northern Virginia; San Antonio; Denver",
    "security_posture": "FedRAMP, NIST 800-53, Zero Trust, FISMA — Moderate lineage",
    "delivery_model": (
        "Embedded agile pods with a shared 24x7 operations center and centralized "
        "platform engineering bench."
    ),
    "pricing_posture": (
        "Competitive value through lean indirects and blended on/off-site staffing."
    ),
}

# Historical outcome bulk data: 22W + 10L + 6NB beyond the 4 showcase completions.
HISTORICAL_OUTCOMES: list[str] = (
    ["won"] * 22 + ["lost"] * 10 + ["no_bid"] * 6
)


@dataclass
class PursuitSpec:
    key: str
    solicitation_number: str
    name: str
    agency: str
    sub_agency: str
    value_cents: int
    capture_stage: str
    outcome: str | None  # won/lost/no_bid or None for active
    loss_reason: str | None = None
    no_bid_reason: str | None = None
    incumbent: str | None = None
    contract_vehicle: str = "GSA MAS"
    flagship: bool = False
    themes: list[str] = field(default_factory=list)


SHOWCASE_PURSUITS: list[PursuitSpec] = [
    PursuitSpec(
        key="cms_cem",
        solicitation_number="APEX-CMS-CEM-2024",
        name="Citizen Engagement Modernization",
        agency="Centers for Medicare Programs",
        sub_agency="Office of Citizen Services",
        value_cents=8_400_000_000,
        capture_stage="won",
        outcome="won",
        incumbent="Horizon Digital Partners",
        contract_vehicle="GSA MAS",
        themes=["Omnichannel CX", "AI self-service", "Workforce optimization"],
    ),
    PursuitSpec(
        key="nasa_esd",
        solicitation_number="APEX-NASA-ESD-2024",
        name="Enterprise Service Desk Transformation",
        agency="National Aviation Services Administration",
        sub_agency="IT Operations",
        value_cents=12_500_000_000,
        capture_stage="lost",
        outcome="lost",
        loss_reason="Incumbent advantage and relationship position.",
        incumbent="Vector Systems Group",
        contract_vehicle="OASIS+",
        themes=["Service desk", "ITIL", "Knowledge management"],
    ),
    PursuitSpec(
        key="vba_bep",
        solicitation_number="APEX-VBA-BEP-2023",
        name="Benefits Experience Platform",
        agency="Veteran Benefits Administration",
        sub_agency="Benefits Delivery",
        value_cents=6_300_000_000,
        capture_stage="won",
        outcome="won",
        incumbent=None,
        contract_vehicle="CIO-SP4",
        themes=["Salesforce", "Benefits CX", "Case management"],
    ),
    PursuitSpec(
        key="dms_mso",
        solicitation_number="APEX-DMS-MSO-2024",
        name="Mission Support Operations",
        agency="Department of Mission Security",
        sub_agency="Operations Directorate",
        value_cents=4_200_000_000,
        capture_stage="no_bid",
        outcome="no_bid",
        no_bid_reason="Capability gap and poor strategic alignment.",
        incumbent="Sentinel Federal Group",
        contract_vehicle="8(a) STARS III",
        themes=["Security operations", "Classified support"],
    ),
    PursuitSpec(
        key="neoa_wsm",
        solicitation_number="APEX-NEOA-WSM-2025",
        name="Workforce Services Modernization",
        agency="National Energy Operations Agency",
        sub_agency="Workforce Services",
        value_cents=9_800_000_000,
        capture_stage="capture",
        outcome=None,
        incumbent="Pinnacle Operations LLC",
        contract_vehicle="OASIS+",
        flagship=True,
        themes=["Workforce transformation", "AI routing", "Change management"],
    ),
    PursuitSpec(
        key="fcsa_det",
        solicitation_number="APEX-FCSA-DET-2025",
        name="Digital Experience Transformation",
        agency="Federal Citizen Services Agency",
        sub_agency="Digital Services",
        value_cents=7_100_000_000,
        capture_stage="proposal",
        outcome=None,
        incumbent="CivicBridge Technologies",
        contract_vehicle="GSA MAS",
        themes=["Digital experience", "Salesforce Experience Cloud"],
    ),
]

PROPOSAL_ASSETS: list[dict[str, Any]] = [
    {"asset_type": "executive_summary", "title": "Mission-First Citizen Experience", "agency": "Centers for Medicare Programs"},
    {"asset_type": "executive_summary", "title": "Zero-Disruption Service Continuity", "agency": "Veteran Benefits Administration"},
    {"asset_type": "executive_summary", "title": "Digital-First Workforce Services", "agency": "National Energy Operations Agency"},
    {"asset_type": "executive_summary", "title": "Trusted Partner for Federal CX", "agency": "Federal Citizen Services Agency"},
    {"asset_type": "executive_summary", "title": "Proven Transition Leadership", "agency": "Centers for Medicare Programs"},
    {"asset_type": "win_theme", "title": "Omnichannel Citizen Journey Excellence"},
    {"asset_type": "win_theme", "title": "AI-Enabled Self-Service at Scale"},
    {"asset_type": "win_theme", "title": "Zero-Disruption Transition Guarantee"},
    {"asset_type": "win_theme", "title": "Workforce Optimization Through Skills-Based Routing"},
    {"asset_type": "win_theme", "title": "Platform-Native Salesforce Delivery"},
    {"asset_type": "transition_approach", "title": "90-Day Phased Transition with Shadow Period"},
    {"asset_type": "transition_approach", "title": "Parallel Operations Knowledge Transfer Model"},
    {"asset_type": "transition_approach", "title": "Hypercare Stabilization Window"},
    {"asset_type": "staffing_approach", "title": "Blended Onshore/Nearshore Contact Center Model"},
    {"asset_type": "staffing_approach", "title": "Tiered Service Desk with Follow-the-Sun Coverage"},
    {"asset_type": "staffing_approach", "title": "Embedded Agile Pods with Shared Platform Bench"},
    {"asset_type": "past_performance", "title": "CMS Citizen Contact Center Modernization"},
    {"asset_type": "past_performance", "title": "VBA Benefits Case Management Platform"},
    {"asset_type": "past_performance", "title": "FCSA Digital Services Portal"},
    {"asset_type": "past_performance", "title": "NEOA Workforce Help Desk Standup"},
    {"asset_type": "past_performance", "title": "Multi-Agency Salesforce Service Cloud Delivery"},
    {"asset_type": "risk_mitigation", "title": "Transition Risk — Dual Operations Runbook"},
    {"asset_type": "risk_mitigation", "title": "Staffing Risk — Surge Bench and Cross-Training"},
    {"asset_type": "risk_mitigation", "title": "Platform Risk — Sandbox-First Release Cadence"},
]

INTELLIGENCE_MODULES: list[str] = [
    "capture.customer_dna",
    "capture.company_dna",
    "capture.compliance_matrix",
    "capture.evaluation_criteria",
    "capture.risk_register",
    "capture.capability_match",
    "capture.win_strategy",
    "capture.executive_brief",
    "capture.gate_review",
    "capture.bid_decision",
]
