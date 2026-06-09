"""Orchestrates module runs: dispatch → persist → audit."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.intelligence import get_registry
from app.intelligence.base import RAGContext
from app.intelligence.citations import build_citations
from app.intelligence.rag import RAGEngine
from app.llm.prompt_library import get_prompt_library
from app.llm.router import get_llm_router
from app.models import AIOutput, Opportunity, User
from app.schemas.intelligence import AIOutputResponse, ModuleSpec


def list_modules() -> list[ModuleSpec]:
    return [
        ModuleSpec(
            id=m.id,
            group=m.group,
            label=m.label,
            description=m.description,
            version=m.version,
            output_schema_summary=m.output_schema_summary,
        )
        for m in get_registry().all()
    ]


def get_module_spec(module_id: str) -> ModuleSpec:
    registry = get_registry()
    cls = registry.get(module_id)
    if cls is None:
        raise NotFoundError(f"Module not registered: {module_id}", code="module.not_found")
    return ModuleSpec(
        id=cls.id,
        group=cls.group,
        label=cls.label,
        description=cls.description,
        version=cls.version,
        output_schema_summary=cls.output_schema_summary,
    )


async def run_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    user: User,
    model_override: str | None = None,
) -> AIOutputResponse:
    registry = get_registry()
    cls = registry.get(module_id)
    if cls is None:
        raise NotFoundError(f"Module not registered: {module_id}", code="module.not_found")
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")

    rag = RAGEngine(db=db, llm_router=get_llm_router())
    module = cls(
        db=db,
        rag=rag,
        llm_router=get_llm_router(),
        prompts=get_prompt_library(),
    )
    ctx = RAGContext(workspace_id=workspace_id, opportunity_id=opportunity_id)
    result = await module.run(opportunity=opp, ctx=ctx, model_override=model_override)

    output_row = AIOutput(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=cls.id,
        module_version=cls.version,
        prompt_id=cls.prompt_id,
        prompt_version=cls.prompt_version,
        model_provider=result.llm.provider,
        model_name=result.llm.model,
        input_tokens=result.llm.input_tokens,
        output_tokens=result.llm.output_tokens,
        latency_ms=result.llm.latency_ms,
        output_json=result.output,
        evidence_chunk_ids=[ev.chunk_id for ev in result.evidence if ev.chunk_id],
        evidence_market_record_ids=[
            ev.market_record_id for ev in result.market_evidence if ev.market_record_id
        ],
        status=result.status,
        generated_by_user_id=user.id,
    )
    db.add(output_row)
    await db.flush()

    return AIOutputResponse(
        id=output_row.id,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=output_row.module_id,
        module_version=output_row.module_version,
        status=output_row.status,  # type: ignore[arg-type]
        model_provider=output_row.model_provider,
        model_name=output_row.model_name,
        input_tokens=output_row.input_tokens,
        output_tokens=output_row.output_tokens,
        latency_ms=output_row.latency_ms,
        output_json=output_row.output_json,
        citations=build_citations(result.evidence, result.market_evidence),
        generated_at=output_row.created_at,
    )


async def latest_for_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
) -> AIOutput | None:
    stmt = (
        select(AIOutput)
        .where(AIOutput.workspace_id == workspace_id)
        .where(AIOutput.opportunity_id == opportunity_id)
        .where(AIOutput.module_id == module_id)
        .order_by(desc(AIOutput.created_at))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def history_for_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    limit: int = 20,
) -> list[AIOutput]:
    stmt = (
        select(AIOutput)
        .where(AIOutput.workspace_id == workspace_id)
        .where(AIOutput.opportunity_id == opportunity_id)
        .where(AIOutput.module_id == module_id)
        .order_by(desc(AIOutput.created_at))
        .limit(min(max(limit, 1), 100))
    )
    return list((await db.execute(stmt)).scalars().all())


def serialize_ai_output(row: AIOutput) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "workspace_id": str(row.workspace_id),
        "opportunity_id": str(row.opportunity_id) if row.opportunity_id else None,
        "module_id": row.module_id,
        "module_version": row.module_version,
        "status": row.status,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "latency_ms": row.latency_ms,
        "output_json": row.output_json,
        "generated_at": row.created_at.isoformat(),
    }
