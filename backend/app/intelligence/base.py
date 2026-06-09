"""Base class for all intelligence modules.

Each module declares its id, group, prompt id+version, output schema, retrieval
query, and result post-processing. The platform's `run_module` orchestrator
calls a uniform `run()` interface, so adding a new module is purely declarative.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.rag import Evidence, RAGEngine
from app.llm.base import LLMResponse
from app.llm.prompt_library import PromptLibrary
from app.llm.router import LLMRouter
from app.models import Opportunity


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

    async def run(
        self,
        *,
        opportunity: Opportunity,
        ctx: RAGContext,
        model_override: str | None = None,
    ) -> ModuleResult:
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

        prompts = self.prompts
        system, user, _ = prompts.render(
            self.prompt_id,
            self.prompt_version,
            opportunity=_safe_opp(opportunity),
            evidence=evidence,
            market_evidence=market_evidence,
        )
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
        "solicitation_number": opp.solicitation_number,
        "naics_code": opp.naics_code,
        "due_date": opp.due_date.isoformat() if opp.due_date else None,
        "estimated_value_cents": opp.estimated_value_cents,
        "incumbent": opp.incumbent,
        "notes": opp.notes,
    }
