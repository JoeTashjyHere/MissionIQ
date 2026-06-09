"""Base class for all intelligence modules.

Each module declares its id, group, prompt id+version, output schema, retrieval
query, and result post-processing. The platform's ``run_module`` orchestrator
calls a uniform ``run()`` interface, so adding a new module is purely
declarative.

Customer DNA dependency
-----------------------

A module that consumes the Customer DNA Profile sets
``requires_customer_dna = True``. The orchestrator then loads the latest
DNA Profile for the opportunity from ``ai_output`` and passes it to the
prompt template as the ``customer_dna`` Jinja variable.

If ``requires_customer_dna`` is True and no DNA Profile exists yet for the
opportunity, the module short-circuits with ``status = "insufficient_context"``
and a clear ``recommended_actions`` payload pointing the user to the DNA
synthesis step. This is the platform's anti-generic-AI guarantee: downstream
modules cannot run without the customer synthesis upstream of them.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.rag import Evidence, RAGEngine
from app.llm.base import LLMResponse
from app.llm.prompt_library import PromptLibrary
from app.llm.router import LLMRouter
from app.models import AIOutput, Opportunity


CUSTOMER_DNA_MODULE_ID = "capture.customer_dna"


@dataclass(slots=True)
class RAGContext:
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    include_market_intel: bool = True
    top_k: int = 12


@dataclass(slots=True)
class ModuleResult:
    output: dict[str, Any]
    evidence: list[Evidence]
    market_evidence: list[Evidence]
    llm: LLMResponse
    status: str = "ok"
    structured_writes: list[Any] = field(default_factory=list)


class _NoopLLMResponse:
    """Synthetic LLMResponse for short-circuit refusals (no LLM call made)."""

    provider = "missioniq"
    model = "no-call"
    input_tokens = 0
    output_tokens = 0
    latency_ms = 0
    text = ""


def _short_circuit_dna_missing() -> dict[str, Any]:
    return {
        "executive_summary": (
            "MissionIQ requires a Customer DNA Profile before producing "
            "consultant-grade output for this module. Generate the Customer "
            "DNA Profile first, then re-run."
        ),
        "key_findings": [],
        "supporting_evidence": [],
        "recommended_actions": [
            "Open the Customer DNA Profile tab and click Generate.",
            "Once the DNA Profile is generated, regenerate this module to "
            "produce mission-aligned analysis.",
        ],
        "_missing_dependency": "customer_dna",
    }


class BaseIntelligenceModule:
    id: ClassVar[str]
    group: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str]
    version: ClassVar[str] = "v1"
    prompt_id: ClassVar[str]
    prompt_version: ClassVar[str] = "v1"
    output_model: ClassVar[type[BaseModel]] | None = None
    output_schema_summary: ClassVar[dict[str, str]] = {}
    retrieval_query: ClassVar[str] = ""
    retrieval_top_k: ClassVar[int] = 12
    minimum_evidence: ClassVar[int] = 2
    # If True, the orchestrator loads the most recent Customer DNA Profile
    # for the opportunity and passes it to the prompt as ``customer_dna``.
    # If no DNA Profile exists yet, the module short-circuits with
    # ``status = "insufficient_context"`` and a clear remediation message.
    requires_customer_dna: ClassVar[bool] = False

    def __init__(
        self,
        *,
        db: AsyncSession,
        rag: RAGEngine,
        llm_router: LLMRouter,
        prompts: PromptLibrary,
    ) -> None:
        self.db = db
        self.rag = rag
        self.llm_router = llm_router
        self.prompts = prompts

    async def _load_customer_dna(
        self, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Return the most recent successful Customer DNA Profile payload, or None."""
        stmt = (
            select(AIOutput)
            .where(AIOutput.workspace_id == workspace_id)
            .where(AIOutput.opportunity_id == opportunity_id)
            .where(AIOutput.module_id == CUSTOMER_DNA_MODULE_ID)
            .where(AIOutput.status == "ok")
            .order_by(desc(AIOutput.created_at))
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        return row.output_json if row else None

    async def run(
        self,
        *,
        opportunity: Opportunity,
        ctx: RAGContext,
        model_override: str | None = None,
    ) -> ModuleResult:
        # 1. Customer DNA prerequisite check (for downstream modules)
        customer_dna: dict[str, Any] | None = None
        if self.requires_customer_dna:
            customer_dna = await self._load_customer_dna(
                workspace_id=ctx.workspace_id,
                opportunity_id=ctx.opportunity_id,
            )
            if customer_dna is None:
                return ModuleResult(
                    output=_short_circuit_dna_missing(),
                    evidence=[],
                    market_evidence=[],
                    llm=LLMResponse(
                        text="",
                        provider="missioniq",
                        model="no-call",
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=0,
                    ),
                    status="insufficient_context",
                )

        # 2. Retrieve grounded evidence
        evidence = await self.rag.retrieve(
            query=self.retrieval_query or self.description,
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            top_k=ctx.top_k or self.retrieval_top_k,
        )
        market_evidence: list[Evidence] = []
        if ctx.include_market_intel:
            market_evidence = await self.rag.retrieve_market(
                query=self.retrieval_query or self.description,
                workspace_id=ctx.workspace_id,
                opportunity_id=ctx.opportunity_id,
                top_k=4,
            )

        status = "ok"
        if len(evidence) < self.minimum_evidence:
            status = "insufficient_context"

        # 3. Render prompt with opportunity + evidence + (optional) DNA
        prompts = self.prompts
        system, user, _ = prompts.render(
            self.prompt_id,
            self.prompt_version,
            opportunity=_safe_opp(opportunity),
            evidence=evidence,
            market_evidence=market_evidence,
            customer_dna=customer_dna,
        )

        # 4. LLM call
        llm = self.llm_router.chat_provider(model_override)
        llm_resp = await llm.generate_json(system=system, user=user)
        try:
            output = json.loads(llm_resp.text)
        except Exception:
            output = {"_error": "model returned non-JSON output", "_raw": llm_resp.text[:2000]}
            status = "error"

        if self.output_model is not None and status == "ok":
            try:
                self.output_model.model_validate(output)
            except Exception as exc:  # noqa: BLE001
                output["_validation_error"] = str(exc)
                status = "error"

        return ModuleResult(
            output=output,
            evidence=evidence,
            market_evidence=market_evidence,
            llm=llm_resp,
            status=status,
        )


def _safe_opp(opp: Opportunity) -> dict[str, Any]:
    return {
        "name": opp.name,
        "agency": opp.agency,
        "sub_agency": opp.sub_agency,
        "solicitation_number": opp.solicitation_number,
        "naics_code": opp.naics_code,
        "due_date": opp.due_date.isoformat() if opp.due_date else None,
        "estimated_value_cents": opp.estimated_value_cents,
        "incumbent": opp.incumbent,
        "notes": opp.notes,
        "capture_stage": opp.capture_stage,
        "contract_vehicle": opp.contract_vehicle,
    }
