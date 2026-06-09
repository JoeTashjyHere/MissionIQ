"""Pursuit Automation Orchestrator schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.connector import AUTOMATION_STATUSES, AUTOMATION_TRIGGERS
from app.schemas.common import ORMModel

AutomationTrigger = Literal[*AUTOMATION_TRIGGERS]  # type: ignore[valid-type]
AutomationStatus = Literal[*AUTOMATION_STATUSES]  # type: ignore[valid-type]

STEP_STATUSES = ("pending", "running", "succeeded", "skipped", "failed")


class AutomationStepResult(BaseModel):
    step_id: str
    label: str
    status: str = "pending"
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    # Link to the produced intelligence (module steps only).
    ai_output_id: str | None = None
    detail: str | None = None


class AutomationRunResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    trigger: str
    status: str
    current_step: str | None
    steps: list[AutomationStepResult]
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    connector_sync_job_id: uuid.UUID | None
    created_at: datetime
    # Denormalized for observability pages.
    opportunity_name: str | None = None
