"""Market intelligence schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MarketIntelSourceResponse(ORMModel):
    id: str
    display_name: str
    classification: str
    auth_mode: str
    enabled: bool


class MarketIntelRecordResponse(ORMModel):
    id: uuid.UUID
    source_id: str
    workspace_id: uuid.UUID | None
    external_id: str
    source_url: str | None
    title: str
    agency: str | None
    sub_agency: str | None
    notice_type: str | None
    naics_code: str | None
    psc_code: str | None
    set_aside: str | None
    estimated_value_cents: int | None
    posted_date: datetime | None
    due_date: datetime | None
    incumbent: str | None
    summary: str | None
    fetched_at: datetime | None


class MarketIntelSearchResponse(BaseModel):
    items: list[MarketIntelRecordResponse]
    source: str
    q: str | None
    total_estimate: int | None = None


class MarketIntelImportRequest(BaseModel):
    source_id: str
    external_ids: list[str] = Field(min_length=1, max_length=200)


class OpportunityMarketIntelLinkCreate(BaseModel):
    market_intel_record_id: uuid.UUID
    notes: str | None = None


class OpportunityMarketIntelLinkResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    market_intel_record_id: uuid.UUID
    notes: str | None
    relevance: float | None
    created_at: datetime
