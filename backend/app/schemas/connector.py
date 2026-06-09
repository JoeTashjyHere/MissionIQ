"""Connector framework schemas.

Credentials are write-only: requests may carry a ``credential`` secret, but
responses expose only derived fields (``credential_set``, ``credential_type``,
``last_validated_at``). The secret never leaves the API boundary.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.connector import (
    CONNECTOR_STATUSES,
    CONNECTOR_TYPES,
    CREDENTIAL_TYPES,
    SYNC_JOB_STATUSES,
    SYNC_JOB_TRIGGERS,
)
from app.schemas.common import ORMModel

ConnectorType = Literal[*CONNECTOR_TYPES]  # type: ignore[valid-type]
ConnectorStatus = Literal[*CONNECTOR_STATUSES]  # type: ignore[valid-type]
CredentialType = Literal[*CREDENTIAL_TYPES]  # type: ignore[valid-type]
SyncJobTrigger = Literal[*SYNC_JOB_TRIGGERS]  # type: ignore[valid-type]
SyncJobStatus = Literal[*SYNC_JOB_STATUSES]  # type: ignore[valid-type]


class ConnectorProviderSpec(BaseModel):
    """Catalog entry from the code-side provider registry."""

    provider_id: str
    label: str
    description: str
    connector_type: str
    auth_mode: str
    phase: int
    implemented: bool
    provides_opportunities: bool
    provides_documents: bool
    requires_customer_authorization: bool = False
    config_fields: list[dict[str, Any]] = []


class ConnectorCreate(BaseModel):
    provider_id: str
    name: str = Field(min_length=1, max_length=200)
    config: dict[str, Any] = {}
    credential: str | None = None  # write-only secret
    auto_create_pursuits: bool = True
    auto_run_automation: bool = False


class ConnectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    credential: str | None = None  # write-only secret rotation
    auto_create_pursuits: bool | None = None
    auto_run_automation: bool | None = None
    enabled: bool | None = None  # False → status "disabled", True → re-enable


class ConnectorResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider_id: str
    connector_type: str
    name: str
    status: str
    config: dict[str, Any]
    auto_create_pursuits: bool
    auto_run_automation: bool
    last_sync_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    # Derived credential metadata (never the secret itself).
    credential_set: bool = False
    credential_type: str = "none"
    last_validated_at: datetime | None = None


class ConnectorTestResult(BaseModel):
    ok: bool
    message: str
    checked_at: datetime


class SyncJobResponse(ORMModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    trigger: str
    status: str
    progress_pct: int
    stats: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    # Denormalized for the Sync History UI.
    connector_name: str | None = None
    provider_id: str | None = None


class ConnectorHealthSummary(BaseModel):
    """Aggregate workspace health for the Connector Health page."""

    total: int
    connected: int
    syncing: int
    failed: int
    disabled: int
    disconnected: int
    jobs_24h: int
    failed_jobs_24h: int
    automation_runs_24h: int
    connectors: list[ConnectorResponse]
