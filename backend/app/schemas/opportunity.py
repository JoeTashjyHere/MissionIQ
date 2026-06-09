"""Opportunity schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.opportunity import CAPTURE_STAGES
from app.schemas.common import ORMModel

CaptureStage = Literal[*CAPTURE_STAGES]  # type: ignore[valid-type]


class OpportunityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    agency: str | None = None
    sub_agency: str | None = None
    contract_vehicle: str | None = None
    solicitation_number: str | None = None
    naics_code: str | None = None
    psc_code: str | None = None
    set_aside: str | None = None
    due_date: datetime | None = None
    posted_date: datetime | None = None
    estimated_value_cents: int | None = Field(default=None, ge=0)
    capture_stage: CaptureStage = "identification"
    incumbent: str | None = None
    notes: str | None = None


class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    agency: str | None = None
    sub_agency: str | None = None
    contract_vehicle: str | None = None
    solicitation_number: str | None = None
    naics_code: str | None = None
    psc_code: str | None = None
    set_aside: str | None = None
    due_date: datetime | None = None
    posted_date: datetime | None = None
    estimated_value_cents: int | None = Field(default=None, ge=0)
    capture_stage: CaptureStage | None = None
    incumbent: str | None = None
    notes: str | None = None


class OpportunityResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    agency: str | None
    sub_agency: str | None
    contract_vehicle: str | None
    solicitation_number: str | None
    naics_code: str | None
    psc_code: str | None
    set_aside: str | None
    due_date: datetime | None
    posted_date: datetime | None
    estimated_value_cents: int | None
    capture_stage: str
    incumbent: str | None
    notes: str | None
    source_type: str = "user_upload"
    source_connector_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class OpportunityOverview(BaseModel):
    opportunity: OpportunityResponse
    document_count: int
    ready_document_count: int
    ai_output_count: int
    risk_count: int
    open_risk_count: int
    compliance_total: int
    compliance_complete: int
    last_ai_generation_at: datetime | None
