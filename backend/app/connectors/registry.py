"""Connector provider registry — the integrations mirror of the intelligence
module registry. Providers self-describe; the API exposes the catalog and the
sync engine resolves instances through this single source of truth."""
from __future__ import annotations

from functools import lru_cache

from app.connectors.base import BaseConnectorProvider
from app.core.errors import NotFoundError


class ConnectorRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, type[BaseConnectorProvider]] = {}

    def register(self, provider_cls: type[BaseConnectorProvider]) -> None:
        if not getattr(provider_cls, "provider_id", None):
            raise ValueError(
                f"{provider_cls.__name__} is missing class-level `provider_id`."
            )
        if provider_cls.provider_id in self._providers:
            raise ValueError(
                f"Provider already registered: {provider_cls.provider_id}"
            )
        self._providers[provider_cls.provider_id] = provider_cls

    def get(self, provider_id: str) -> type[BaseConnectorProvider] | None:
        return self._providers.get(provider_id)

    def require(self, provider_id: str) -> type[BaseConnectorProvider]:
        cls = self.get(provider_id)
        if cls is None:
            raise NotFoundError(f"Unknown connector provider: {provider_id}")
        return cls

    def all(self) -> list[type[BaseConnectorProvider]]:
        return list(self._providers.values())


@lru_cache
def get_connector_registry() -> ConnectorRegistry:
    """Register every connector provider, Phase 1 first (catalog order)."""
    registry = ConnectorRegistry()

    from app.connectors.providers.local_repository import (  # noqa: E402
        LocalRepositoryProvider,
    )
    from app.connectors.providers.planned import (  # noqa: E402
        BloombergGovProvider,
        DynamicsProvider,
        GovWinProvider,
        JiraProvider,
        ServiceNowProvider,
    )
    from app.connectors.providers.salesforce import SalesforceProvider  # noqa: E402
    from app.connectors.providers.sharepoint import SharePointProvider  # noqa: E402

    # Phase 1 — implemented
    registry.register(SalesforceProvider)
    registry.register(SharePointProvider)
    registry.register(LocalRepositoryProvider)
    # Phase 2 — planned extension points
    registry.register(GovWinProvider)
    registry.register(BloombergGovProvider)
    # Phase 3 — planned extension points
    registry.register(ServiceNowProvider)
    registry.register(DynamicsProvider)
    registry.register(JiraProvider)
    return registry
