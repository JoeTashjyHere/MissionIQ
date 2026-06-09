"""Phase 2 and Phase 3 connector extension points.

These providers are registered as catalog descriptors only
(``implemented = False``): they appear in the provider catalog and the
Integrations UI as planned integrations, declare their connector type, auth
mode, and configuration surface, and raise a structured
``connector.not_implemented`` error if exercised. Implementing one later means
subclassing the descriptor and filling in the three provider operations — no
framework, schema, or API change.
"""
from __future__ import annotations

from typing import Any, ClassVar

from app.connectors.base import PlannedConnectorProvider

# ── Phase 2 — market intelligence ──────────────────────────────────────────


class GovWinProvider(PlannedConnectorProvider):
    provider_id: ClassVar[str] = "govwin"
    label: ClassVar[str] = "GovWin IQ"
    description: ClassVar[str] = (
        "Market intelligence connector for Deltek GovWin IQ. Customer-"
        "authorized access only: a workspace may connect exclusively with its "
        "own GovWin entitlement and credentials."
    )
    connector_type: ClassVar[str] = "market_intelligence"
    auth_mode: ClassVar[str] = "api_key"
    phase: ClassVar[int] = 2
    provides_opportunities: ClassVar[bool] = True
    requires_customer_authorization: ClassVar[bool] = True
    config_fields: ClassVar[list[dict[str, Any]]] = [
        {"key": "client_id", "label": "GovWin client ID", "required": True},
    ]


class BloombergGovProvider(PlannedConnectorProvider):
    provider_id: ClassVar[str] = "bloomberg_gov"
    label: ClassVar[str] = "Bloomberg Government"
    description: ClassVar[str] = (
        "Market intelligence connector for Bloomberg Government contract and "
        "budget data."
    )
    connector_type: ClassVar[str] = "market_intelligence"
    auth_mode: ClassVar[str] = "api_key"
    phase: ClassVar[int] = 2
    provides_opportunities: ClassVar[bool] = True


# ── Phase 3 — service / project / CRM platforms ────────────────────────────


class ServiceNowProvider(PlannedConnectorProvider):
    provider_id: ClassVar[str] = "servicenow"
    label: ClassVar[str] = "ServiceNow"
    description: ClassVar[str] = (
        "Knowledge management connector for ServiceNow — delivery and "
        "operations records feeding the Deliver and Improve phases."
    )
    connector_type: ClassVar[str] = "knowledge_management"
    auth_mode: ClassVar[str] = "oauth"
    phase: ClassVar[int] = 3
    provides_documents: ClassVar[bool] = True
    config_fields: ClassVar[list[dict[str, Any]]] = [
        {"key": "instance_url", "label": "Instance URL", "required": True},
    ]


class DynamicsProvider(PlannedConnectorProvider):
    provider_id: ClassVar[str] = "dynamics"
    label: ClassVar[str] = "Microsoft Dynamics 365"
    description: ClassVar[str] = (
        "CRM connector for Dynamics 365 Sales — the Dynamics counterpart to "
        "the Salesforce pursuit automation flow."
    )
    connector_type: ClassVar[str] = "crm"
    auth_mode: ClassVar[str] = "oauth"
    phase: ClassVar[int] = 3
    provides_opportunities: ClassVar[bool] = True
    provides_documents: ClassVar[bool] = True


class JiraProvider(PlannedConnectorProvider):
    provider_id: ClassVar[str] = "jira"
    label: ClassVar[str] = "Jira"
    description: ClassVar[str] = (
        "Project management connector for Jira — proposal and delivery task "
        "signals for future Operations Intelligence modules."
    )
    connector_type: ClassVar[str] = "project_management"
    auth_mode: ClassVar[str] = "api_key"
    phase: ClassVar[int] = 3
    provides_documents: ClassVar[bool] = False
