"""Module registry. Every intelligence module self-registers; the API exposes
``/modules`` and ``/modules/{id}/run`` over this single source of truth."""
from __future__ import annotations

from functools import lru_cache

from app.intelligence.base import BaseIntelligenceModule


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, type[BaseIntelligenceModule]] = {}

    def register(self, module_cls: type[BaseIntelligenceModule]) -> None:
        if not getattr(module_cls, "id", None):
            raise ValueError(f"{module_cls.__name__} is missing class-level `id`.")
        if module_cls.id in self._modules:
            raise ValueError(f"Module already registered: {module_cls.id}")
        self._modules[module_cls.id] = module_cls

    def get(self, module_id: str) -> type[BaseIntelligenceModule] | None:
        return self._modules.get(module_id)

    def all(self) -> list[type[BaseIntelligenceModule]]:
        return list(self._modules.values())


@lru_cache
def get_registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    from app.intelligence.modules.capture.opportunity_summary import (  # noqa: E402
        OpportunitySummaryModule,
    )

    registry.register(OpportunitySummaryModule)
    return registry
