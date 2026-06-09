"""Intelligence module + AI output schemas."""
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


# ── Module-specific output schemas ──


class SupportingEvidenceItem(BaseModel):
    """Single piece of supporting evidence as cited by the model.

    `evidence_ref` is the canonical pointer (e.g. ``E1`` or ``M2``) into the
    EVIDENCE block of the prompt. The platform validates these refs against
    the actual retrieved evidence at persistence time.
    """

    evidence_ref: str
    finding: str


class OpportunitySummaryOutput(BaseModel):
    """Canonical four-section executive briefing.

    The platform contract for every briefing-style module is:

    - ``executive_summary`` — the bottom line a busy executive needs in 30s
    - ``key_findings``      — discrete, evidence-backed findings
    - ``supporting_evidence`` — explicit pointers back to source evidence
    - ``recommended_actions`` — what the team should do next

    Rich fields (mission_need, scope_summary, deliverables, etc.) remain as
    structured supplemental data the UI can surface as expanded detail.
    """

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
