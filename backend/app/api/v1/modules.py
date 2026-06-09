"""Intelligence module endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser, OppScope
from app.core.errors import NotFoundError
from app.intelligence.citations import build_citations
from app.schemas.intelligence import (
    AIOutputResponse,
    ModuleSpec,
    RunModuleRequest,
)
from app.services import intelligence_service
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("/modules", response_model=list[ModuleSpec])
async def list_modules() -> list[ModuleSpec]:
    return intelligence_service.list_modules()


@router.get("/modules/{module_id}", response_model=ModuleSpec)
async def get_module(module_id: Annotated[str, Path()]) -> ModuleSpec:
    return intelligence_service.get_module_spec(module_id)


@router.post(
    "/opportunities/{opportunity_id}/modules/{module_id}/run",
    response_model=AIOutputResponse,
)
async def run_module(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: RunModuleRequest | None = None,
) -> AIOutputResponse:
    ws, _, opportunity_id = scope
    payload = payload or RunModuleRequest()
    resp = await intelligence_service.run_module(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        module_id=module_id,
        user=user,
        model_override=payload.model_override,
    )
    await write_audit(
        db,
        action="ai.module.run",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="ai_output",
        target_id=resp.id,
        meta={
            "module_id": module_id,
            "status": resp.status,
            "model": f"{resp.model_provider}/{resp.model_name}",
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        },
    )
    return resp


@router.get(
    "/opportunities/{opportunity_id}/modules/{module_id}/latest",
    response_model=AIOutputResponse | None,
)
async def latest_module_output(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIOutputResponse | None:
    ws, _, opportunity_id = scope
    row = await intelligence_service.latest_for_module(
        db, workspace_id=ws.id, opportunity_id=opportunity_id, module_id=module_id
    )
    if row is None:
        return None
    # Build citations from stored evidence ids
    citations = []
    if row.evidence_chunk_ids:
        from sqlalchemy import select
        from app.models import Document, DocumentChunk

        stmt = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.id.in_(row.evidence_chunk_ids))
        )
        result = (await db.execute(stmt)).all()
        from app.schemas.common import DocumentCitation

        for chunk, doc in result:
            citations.append(
                DocumentCitation(
                    id=chunk.id,
                    document_id=doc.id,
                    document_name=doc.name,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_path=chunk.section_path,
                    snippet=(chunk.text or "")[:600],
                )
            )

    return AIOutputResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        opportunity_id=row.opportunity_id,
        module_id=row.module_id,
        module_version=row.module_version,
        status=row.status,  # type: ignore[arg-type]
        model_provider=row.model_provider,
        model_name=row.model_name,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        latency_ms=row.latency_ms,
        output_json=row.output_json,
        citations=citations,
        generated_at=row.created_at,
    )


@router.get(
    "/opportunities/{opportunity_id}/modules/{module_id}/history",
    response_model=list[AIOutputResponse],
)
async def history_module_output(
    module_id: Annotated[str, Path()],
    scope: OppScope,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AIOutputResponse]:
    ws, _, opportunity_id = scope
    rows = await intelligence_service.history_for_module(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        module_id=module_id,
        limit=limit,
    )
    return [
        AIOutputResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            opportunity_id=r.opportunity_id,
            module_id=r.module_id,
            module_version=r.module_version,
            status=r.status,  # type: ignore[arg-type]
            model_provider=r.model_provider,
            model_name=r.model_name,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            latency_ms=r.latency_ms,
            output_json=r.output_json,
            citations=[],
            generated_at=r.created_at,
        )
        for r in rows
    ]
