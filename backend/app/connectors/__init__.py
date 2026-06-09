"""Connector framework: provider contract + registry.

Workspace-scoped connector *instances* live in the database
(``app/models/connector.py``); provider *behavior* lives here.
"""
from app.connectors.base import (
    BaseConnectorProvider,
    ConnectorHealth,
    DiscoveryResult,
    ExternalDocument,
    ExternalOpportunity,
    PlannedConnectorProvider,
)
from app.connectors.registry import ConnectorRegistry, get_connector_registry

__all__ = [
    "BaseConnectorProvider",
    "ConnectorHealth",
    "ConnectorRegistry",
    "DiscoveryResult",
    "ExternalDocument",
    "ExternalOpportunity",
    "PlannedConnectorProvider",
    "get_connector_registry",
]
