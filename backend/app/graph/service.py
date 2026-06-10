"""Knowledge-graph persistence: idempotent ingestion + query helpers.

Entities are deduplicated per workspace by ``(entity_type, normalized_key)``
and accumulate attributes + mention counts over time. Edges are stamped with
their ``(opportunity_id, module_id)`` provenance so a module re-run replaces
exactly its own contributions — the graph never double-counts.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.extract import (
    EntitySpec,
    FactBundle,
    extract_facts,
    extract_opportunity_base,
)
from app.models import GraphEdge, GraphEntity, Opportunity


def opportunity_meta(opp: Opportunity) -> dict[str, Any]:
    """The plain-dict view of an opportunity the pure extractors expect."""
    return {
        "id": opp.id,
        "name": opp.name,
        "agency": opp.agency,
        "sub_agency": opp.sub_agency,
        "contract_vehicle": opp.contract_vehicle,
        "incumbent": opp.incumbent,
        "naics_code": opp.naics_code,
        "capture_stage": opp.capture_stage,
    }


def _merge_attrs(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing or {})
    for k, v in (incoming or {}).items():
        if v is not None and v != [] and v != "":
            merged[k] = v
    return merged


async def _upsert_entity(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    spec: EntitySpec,
    cache: dict[tuple[str, str], uuid.UUID],
) -> uuid.UUID:
    key = (spec.entity_type, spec.key)
    if key in cache:
        # Still merge any new attributes onto the already-resolved row.
        if spec.attributes:
            row = await db.get(GraphEntity, cache[key])
            if row is not None:
                row.attributes = _merge_attrs(row.attributes, spec.attributes)
        return cache[key]

    row = (
        await db.execute(
            select(GraphEntity)
            .where(GraphEntity.workspace_id == workspace_id)
            .where(GraphEntity.entity_type == spec.entity_type)
            .where(GraphEntity.normalized_key == spec.key)
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if row is None:
        row = GraphEntity(
            workspace_id=workspace_id,
            entity_type=spec.entity_type,
            name=spec.name,
            normalized_key=spec.key,
            attributes=_merge_attrs({}, spec.attributes),
            mention_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(row)
        await db.flush()
    else:
        row.attributes = _merge_attrs(row.attributes, spec.attributes)
        row.mention_count = (row.mention_count or 0) + 1
        row.last_seen_at = now

    cache[key] = row.id
    return row.id


async def _persist(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    bundle: FactBundle,
) -> int:
    # Idempotency: clear this provenance's prior edges before re-adding.
    await db.execute(
        delete(GraphEdge)
        .where(GraphEdge.workspace_id == workspace_id)
        .where(GraphEdge.opportunity_id == opportunity_id)
        .where(GraphEdge.module_id == module_id)
    )

    cache: dict[tuple[str, str], uuid.UUID] = {}
    for spec in bundle.entities:
        await _upsert_entity(db, workspace_id=workspace_id, spec=spec, cache=cache)

    edge_count = 0
    for edge in bundle.edges:
        src_id = await _upsert_entity(
            db, workspace_id=workspace_id, spec=edge.source, cache=cache
        )
        tgt_id = await _upsert_entity(
            db, workspace_id=workspace_id, spec=edge.target, cache=cache
        )
        db.add(
            GraphEdge(
                workspace_id=workspace_id,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relation=edge.relation,
                opportunity_id=opportunity_id,
                module_id=module_id,
                attributes=edge.attributes or {},
            )
        )
        edge_count += 1

    await db.flush()
    return edge_count


async def ingest_opportunity_base(
    db: AsyncSession, *, workspace_id: uuid.UUID, opp: Opportunity
) -> int:
    """Ingest agency / vehicle / incumbent facts from the opportunity record."""
    bundle = extract_opportunity_base(opportunity_meta(opp))
    return await _persist(
        db,
        workspace_id=workspace_id,
        opportunity_id=opp.id,
        module_id="opportunity",
        bundle=bundle,
    )


async def ingest_proposal_bundle(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    bundle: FactBundle,
) -> int:
    """Ingest proposal-extraction graph facts (idempotent per provenance)."""
    return await _persist(
        db,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=module_id,
        bundle=bundle,
    )


async def ingest_module_output(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opp: Opportunity,
    module_id: str,
    output: dict[str, Any],
) -> int:
    """Ingest a module's structured output into the graph (idempotent)."""
    # Always refresh the opportunity base first so agency/vehicle/incumbent
    # nodes exist for the memory layer even if only one module has run.
    await ingest_opportunity_base(db, workspace_id=workspace_id, opp=opp)
    bundle = extract_facts(module_id, output, opportunity_meta(opp))
    return await _persist(
        db,
        workspace_id=workspace_id,
        opportunity_id=opp.id,
        module_id=module_id,
        bundle=bundle,
    )


# ── Query helpers (used by the memory service) ────────────────────────────


async def workspace_edges(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> list[GraphEdge]:
    return list(
        (
            await db.execute(
                select(GraphEdge).where(GraphEdge.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )


async def entities_by_id(
    db: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, GraphEntity]:
    if not ids:
        return {}
    rows = (
        await db.execute(select(GraphEntity).where(GraphEntity.id.in_(ids)))
    ).scalars().all()
    return {r.id: r for r in rows}


async def graph_stats(db: AsyncSession, *, workspace_id: uuid.UUID) -> dict[str, int]:
    rows = (
        await db.execute(
            select(GraphEntity.entity_type, func.count())
            .where(GraphEntity.workspace_id == workspace_id)
            .group_by(GraphEntity.entity_type)
        )
    ).all()
    return {etype: count for etype, count in rows}
