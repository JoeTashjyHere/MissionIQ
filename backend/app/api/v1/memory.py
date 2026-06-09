"""Memory + Knowledge Graph endpoints.

These power the reusable intelligence layer — Pursuit Memory, the Opportunity
Similarity Engine, the Historical Insight Repository, and the Agency
Intelligence Repository — that make MissionIQ smarter with every opportunity.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import OppScope, WorkspaceScope
from app.schemas.memory import HistoricalInsightRepository, PursuitMemory
from app.services import memory_service

router = APIRouter()


@router.get("/opportunities/{opportunity_id}/memory", response_model=PursuitMemory)
async def pursuit_memory(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> PursuitMemory:
    ws, _, opportunity_id = scope
    return await memory_service.build_pursuit_memory(
        db, workspace_id=ws.id, opportunity_id=opportunity_id
    )


@router.get(
    "/workspaces/{workspace_id}/insights",
    response_model=HistoricalInsightRepository,
)
async def historical_insights(
    scope: WorkspaceScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> HistoricalInsightRepository:
    ws, _ = scope
    return await memory_service.historical_insights(db, workspace_id=ws.id)
