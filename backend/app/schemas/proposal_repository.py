"""Proposal Intelligence Repository schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

AssetType = Literal[
    "executive_summary",
    "win_theme",
    "staffing_approach",
    "transition_approach",
    "management_approach",
    "technical_approach",
    "past_performance",
    "risk_mitigation",
    "discriminator",
    "pricing_narrative",
    "lessons_learned",
    "custom",
]


class AssetCitationResponse(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_name: str | None = None
    chunk_id: uuid.UUID | None
    page_start: int | None
    page_end: int | None
    section_path: str | None
    excerpt: str


class AssetUsageResponse(ORMModel):
    opportunity_id: uuid.UUID
    opportunity_name: str | None = None
    usage_kind: str
    outcome: str | None = None
    created_at: datetime


class ProposalAssetResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    asset_type: str
    title: str
    summary: str
    content: dict[str, Any]
    document_id: uuid.UUID
    document_name: str | None = None
    opportunity_id: uuid.UUID | None
    opportunity_name: str | None = None
    agency: str | None
    customer_name: str | None
    submission_date: datetime | None
    outcome: str | None
    author: str | None
    version: str | None
    source_type: str
    tags: list[str]
    extraction_confidence: str
    extraction_basis: str
    wins: int
    losses: int
    usage_count: int
    win_rate: float | None
    outcome_weight: float
    track_record: str | None = None
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProposalAssetDetail(ProposalAssetResponse):
    citations: list[AssetCitationResponse] = []
    usages: list[AssetUsageResponse] = []
    similar_assets: list[ProposalAssetResponse] = []


class AssetSearchParams(BaseModel):
    q: str | None = None
    asset_type: str | None = None
    agency: str | None = None
    outcome: str | None = None
    min_win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    author: str | None = None
    tags: list[str] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    search_mode: Literal["hybrid", "text", "semantic"] = "hybrid"
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ExtractedAssetCitation(BaseModel):
    excerpt: str
    page_start: int | None = None
    page_end: int | None = None
    section_path: str | None = None


class ExtractedAsset(BaseModel):
    asset_type: AssetType
    title: str
    summary: str
    content: dict[str, Any] = {}
    confidence: Literal["high", "medium", "low"] = "medium"
    basis: Literal["evidence", "inference", "assumption"] = "evidence"
    citations: list[ExtractedAssetCitation] = []
    tags: list[str] = []


class ProposalExtractionOutput(BaseModel):
    assets: list[ExtractedAsset] = []
    document_summary: str | None = None
    inputs_missing: list[str] = []


class RepositorySummary(BaseModel):
    total_assets: int
    pursuits_with_assets: int
    assets_with_outcome_signal: int
    avg_win_rate: float | None


class AssetPattern(BaseModel):
    asset_id: uuid.UUID
    title: str
    asset_type: str
    agency: str | None
    wins: int
    losses: int
    usage_count: int
    win_rate: float | None
    outcome_weight: float
    observation: str
    source_pursuits: list[str] = []


class ProposalIntelligenceReport(BaseModel):
    summary: RepositorySummary
    top_win_themes: list[AssetPattern] = []
    top_transition_approaches: list[AssetPattern] = []
    top_staffing_approaches: list[AssetPattern] = []
    top_executive_summaries: list[AssetPattern] = []
    agency_patterns: list[AssetPattern] = []
    historical_observations: list[str] = []


class ProposalQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    agency: str | None = None
    asset_types: list[AssetType] = []


class ProposalIntelligenceOutput(BaseModel):
    query_summary: str
    relevant_assets: list[AssetPattern] = []
    agency_patterns: list[str] = []
    historical_observations: list[str] = []
    reusable_recommendations: list[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"
    inputs_missing: list[str] = []
    citations: list[dict[str, str]] = []
