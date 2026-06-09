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
    """Register every intelligence module.

    Order matters for the UI: the Customer DNA Profile is registered first
    because every downstream Capture module consumes it. The order also
    determines the order of the ``/modules`` API response, which the
    frontend uses to render the opportunity sub-navigation.
    """
    registry = ModuleRegistry()

    # Synthesis steps (read by everything else)
    from app.intelligence.modules.capture.customer_dna import (  # noqa: E402
        CustomerDnaModule,
    )
    from app.intelligence.modules.capture.company_dna import (  # noqa: E402
        CompanyDnaModule,
    )

    # Briefing-style modules
    from app.intelligence.modules.capture.opportunity_summary import (  # noqa: E402
        OpportunitySummaryModule,
    )

    # Insight-grade modules (require Customer DNA)
    from app.intelligence.modules.capture.compliance_matrix import (  # noqa: E402
        ComplianceMatrixModule,
    )
    from app.intelligence.modules.capture.evaluation_criteria import (  # noqa: E402
        EvaluationCriteriaModule,
    )
    from app.intelligence.modules.capture.risk_register import (  # noqa: E402
        RiskRegisterModule,
    )

    # Seller × customer fit engine (requires Customer DNA, consumes Company)
    from app.intelligence.modules.capture.capability_match import (  # noqa: E402
        CapabilityMatchModule,
    )

    # Flagship synthesis — reads every upstream module
    from app.intelligence.modules.capture.win_strategy import (  # noqa: E402
        WinStrategyModule,
    )

    # Executive briefings & gate reviews — leadership decision packages that
    # synthesize every upstream output (including Win Strategy) into decisions.
    from app.intelligence.modules.capture.briefings import (  # noqa: E402
        BidDecisionModule,
        ExecutiveBriefModule,
        GateReviewModule,
    )

    registry.register(CustomerDnaModule)
    registry.register(CompanyDnaModule)
    registry.register(OpportunitySummaryModule)
    registry.register(ComplianceMatrixModule)
    registry.register(EvaluationCriteriaModule)
    registry.register(RiskRegisterModule)
    registry.register(CapabilityMatchModule)
    registry.register(WinStrategyModule)
    registry.register(ExecutiveBriefModule)
    registry.register(GateReviewModule)
    registry.register(BidDecisionModule)
    return registry
