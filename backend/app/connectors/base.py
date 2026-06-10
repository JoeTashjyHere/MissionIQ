"""Connector provider contract.

Providers are the code-side behavior of the connector framework — the mirror of
``app/intelligence/base.py`` for integrations. A provider declares a descriptor
(ClassVars) and implements three operations against normalized, pure data
shapes so the sync engine, orchestrator, and tests never touch provider wire
formats:

- ``test_connection``  → ConnectorHealth (used by Connected/Failed state + UI)
- ``discover``         → DiscoveryResult of ExternalOpportunity / ExternalDocument
- ``fetch_document``   → raw bytes, ingested through the existing pipeline

Phase 2/3 providers register descriptors with ``implemented = False`` — they
appear in the catalog as planned extension points and raise a structured error
if exercised.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from app.core.errors import AppError

AUTH_MODES = ("api_key", "oauth", "basic", "none")


@dataclass
class ExternalOpportunity:
    """A normalized opportunity-like record discovered by a provider."""

    external_id: str
    name: str
    agency: str | None = None
    sub_agency: str | None = None
    contract_vehicle: str | None = None
    solicitation_number: str | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    due_date: datetime | None = None
    estimated_value_cents: int | None = None
    incumbent: str | None = None
    capture_stage: str | None = None
    notes: str | None = None
    # External document refs attached to this opportunity (fetched separately).
    attachments: list[ExternalDocument] = field(default_factory=list)


@dataclass
class ExternalDocument:
    """A normalized document reference discovered by a provider."""

    external_id: str
    filename: str
    mime_type: str = "text/plain"
    doc_type: str = "other"
    # Provider-specific fetch reference (path, URL, record id, …).
    fetch_ref: str = ""
    # When the external opportunity is known, links the doc to that pursuit.
    opportunity_external_id: str | None = None
    # Fallback pursuit resolution for document repositories: the folder or
    # library name, matched against existing opportunity names.
    opportunity_name_hint: str | None = None
    # When ``proposal_repository``, the sync engine tags the document as a
    # proposal artifact so extraction runs after ingestion (SharePoint archives).
    ingest_mode: str | None = None


@dataclass
class DiscoveryResult:
    opportunities: list[ExternalOpportunity] = field(default_factory=list)
    documents: list[ExternalDocument] = field(default_factory=list)


@dataclass
class ConnectorHealth:
    ok: bool
    message: str


class ConnectorNotImplementedError(AppError):
    status_code = 501
    code = "connector.not_implemented"
    title = "Connector not implemented"


class BaseConnectorProvider(ABC):
    """Contract every connector provider implements."""

    provider_id: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str] = ""
    connector_type: ClassVar[str]  # one of models.connector.CONNECTOR_TYPES
    auth_mode: ClassVar[str] = "none"  # one of AUTH_MODES
    phase: ClassVar[int] = 1
    implemented: ClassVar[bool] = True
    provides_opportunities: ClassVar[bool] = False
    provides_documents: ClassVar[bool] = False
    # True when the provider can discover historical proposal archives for the
    # Proposal Intelligence Repository (extension point — not implemented here).
    provides_proposal_archives: ClassVar[bool] = False
    requires_customer_authorization: ClassVar[bool] = False
    # Declarative form spec for the UI: [{key, label, placeholder, required}].
    config_fields: ClassVar[list[dict[str, Any]]] = []

    @abstractmethod
    async def test_connection(
        self, *, config: dict[str, Any], secret: str | None
    ) -> ConnectorHealth:
        """Validate configuration + credentials without ingesting anything."""

    @abstractmethod
    async def discover(
        self,
        *,
        config: dict[str, Any],
        secret: str | None,
        since: datetime | None = None,
    ) -> DiscoveryResult:
        """Return normalized opportunities/documents new or changed since
        ``since`` (None → full discovery)."""

    @abstractmethod
    async def fetch_document(
        self, *, config: dict[str, Any], secret: str | None, ref: ExternalDocument
    ) -> bytes:
        """Fetch raw document bytes for an ExternalDocument reference."""


class PlannedConnectorProvider(BaseConnectorProvider):
    """Base for Phase 2/3 extension points: catalog descriptor only."""

    implemented: ClassVar[bool] = False

    def _not_implemented(self) -> ConnectorNotImplementedError:
        return ConnectorNotImplementedError(
            f"The {self.label} connector is a planned integration. "
            "Its provider descriptor reserves the extension point; the "
            "implementation ships in a later phase."
        )

    async def test_connection(
        self, *, config: dict[str, Any], secret: str | None
    ) -> ConnectorHealth:
        raise self._not_implemented()

    async def discover(
        self,
        *,
        config: dict[str, Any],
        secret: str | None,
        since: datetime | None = None,
    ) -> DiscoveryResult:
        raise self._not_implemented()

    async def fetch_document(
        self, *, config: dict[str, Any], secret: str | None, ref: ExternalDocument
    ) -> bytes:
        raise self._not_implemented()
