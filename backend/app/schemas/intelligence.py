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

class OpportunitySummaryOutput(BaseModel):
    executive_summary: str
    mission_need: str
    scope_summary: str
    key_services: list[str]
    deliverables: list[str]
    timeline: str
    risks: list[str]
    pursue_indicators: list[str]
    no_pursue_indicators: list[str]
    key_findings: list[str]
    recommended_actions: list[str]
    citations: list[dict] = []
