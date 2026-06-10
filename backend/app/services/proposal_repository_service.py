"""Proposal Intelligence Repository — deterministic layer.

Search, outcome statistics, workspace reports, and compact context for
consuming modules. No LLM — pure statistics and retrieval, same role as
``outcome_intelligence_service`` in the outcome milestone.
"""
from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.graph.extract import normalize_key
from app.intelligence.rag import _vec_literal
from app.models import (
    Document,
    Opportunity,
    ProposalAsset,
    ProposalAssetCitation,
    ProposalAssetUsage,
    PursuitOutcome,
)
from app.models.outcome import DECIDED_OUTCOMES
from app.models.proposal_asset import ASSET_TYPES
from app.schemas.proposal_repository import (
    AssetCitationResponse,
    AssetPattern,
    AssetSearchParams,
    AssetUsageResponse,
    ProposalAssetDetail,
    ProposalAssetResponse,
    ProposalIntelligenceReport,
    RepositorySummary,
)
from app.services.outcome_intelligence_service import (
    compute_win_rate,
    laplace_weight,
    observation_text,
)

LIBRARY_FILTERS: dict[str, tuple[str, ...]] = {
    "all": ASSET_TYPES,
    "past_performance": ("past_performance",),
    "win_themes": ("win_theme", "discriminator"),
    "staffing": ("staffing_approach", "management_approach"),
    "transition": ("transition_approach",),
    "executive_summaries": ("executive_summary",),
}


def asset_normalized_key(asset_type: str, title: str) -> str:
    normalized = normalize_key(title)
    return hashlib.sha256(f"{asset_type}|{normalized}".encode()).hexdigest()


def format_track_record(wins: int, losses: int, usage_count: int) -> str | None:
    decided = wins + losses
    if decided == 0 and usage_count == 0:
        return None
    parts = [f"Used in {usage_count} pursuit{'s' if usage_count != 1 else ''}"]
    if decided:
        rate = compute_win_rate(wins, losses)
        rate_txt = f" · {round(rate * 100)}% historical win rate" if rate is not None else ""
        parts.append(f"{wins}W–{losses}L{rate_txt}")
    return "".join(parts)


def compute_asset_outcome_stats(
    usages: list[tuple[uuid.UUID, str | None]],
) -> tuple[int, int, int, float | None, float]:
    """From (opportunity_id, outcome) pairs → wins, losses, usage_count, win_rate, weight."""
    by_opp: dict[uuid.UUID, str | None] = {}
    for opp_id, outcome in usages:
        by_opp[opp_id] = outcome
    usage_count = len(by_opp)
    wins = sum(1 for o in by_opp.values() if o == "won")
    losses = sum(1 for o in by_opp.values() if o == "lost")
    return (
        wins,
        losses,
        usage_count,
        compute_win_rate(wins, losses),
        laplace_weight(wins, losses),
    )


async def recompute_asset_outcomes(db: AsyncSession, *, workspace_id: uuid.UUID) -> int:
    """Idempotent full rescan of proposal asset outcome statistics."""
    await db.execute(
        update(ProposalAsset)
        .where(ProposalAsset.workspace_id == workspace_id)
        .values(wins=0, losses=0, usage_count=0, win_rate=None, outcome_weight=1.0)
    )
    outcome_by_opp = {
        po.opportunity_id: po.outcome
        for po in (
            await db.execute(
                select(PursuitOutcome).where(PursuitOutcome.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    }
    usages = list(
        (
            await db.execute(
                select(ProposalAssetUsage).where(
                    ProposalAssetUsage.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    by_asset: dict[uuid.UUID, list[tuple[uuid.UUID, str | None]]] = defaultdict(list)
    for u in usages:
        outcome = outcome_by_opp.get(u.opportunity_id)
        by_asset[u.asset_id].append((u.opportunity_id, outcome))

    updated = 0
    for asset_id, pairs in by_asset.items():
        wins, losses, usage_count, win_rate, weight = compute_asset_outcome_stats(pairs)
        await db.execute(
            update(ProposalAsset)
            .where(ProposalAsset.id == asset_id)
            .values(
                wins=wins,
                losses=losses,
                usage_count=usage_count,
                win_rate=win_rate,
                outcome_weight=weight,
            )
        )
        updated += 1
    await db.flush()
    return updated


async def sync_asset_outcomes_from_opportunity(
    db: AsyncSession, *, opportunity_id: uuid.UUID
) -> None:
    """Refresh denormalized outcome on assets linked to one pursuit."""
    po = (
        await db.execute(
            select(PursuitOutcome).where(PursuitOutcome.opportunity_id == opportunity_id)
        )
    ).scalar_one_or_none()
    outcome = po.outcome if po else None
    asset_ids = list(
        (
            await db.execute(
                select(ProposalAssetUsage.asset_id).where(
                    ProposalAssetUsage.opportunity_id == opportunity_id
                )
            )
        )
        .scalars()
        .all()
    )
    if asset_ids:
        await db.execute(
            update(ProposalAsset)
            .where(ProposalAsset.id.in_(asset_ids))
            .values(outcome=outcome)
        )
    ws_id = (
        await db.execute(
            select(Opportunity.workspace_id).where(Opportunity.id == opportunity_id)
        )
    ).scalar_one()
    await recompute_asset_outcomes(db, workspace_id=ws_id)


def _to_response(
    asset: ProposalAsset,
    *,
    document_name: str | None = None,
    opportunity_name: str | None = None,
    last_used_at: datetime | None = None,
) -> ProposalAssetResponse:
    return ProposalAssetResponse(
        id=asset.id,
        workspace_id=asset.workspace_id,
        asset_type=asset.asset_type,
        title=asset.title,
        summary=asset.summary,
        content=asset.content or {},
        document_id=asset.document_id,
        document_name=document_name,
        opportunity_id=asset.opportunity_id,
        opportunity_name=opportunity_name,
        agency=asset.agency,
        customer_name=asset.customer_name,
        submission_date=asset.submission_date,
        outcome=asset.outcome,
        author=asset.author,
        version=asset.version,
        source_type=asset.source_type,
        tags=list(asset.tags or []),
        extraction_confidence=asset.extraction_confidence,
        extraction_basis=asset.extraction_basis,
        wins=asset.wins,
        losses=asset.losses,
        usage_count=asset.usage_count,
        win_rate=asset.win_rate,
        outcome_weight=asset.outcome_weight,
        track_record=format_track_record(asset.wins, asset.losses, asset.usage_count),
        last_used_at=last_used_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


async def enrich_assets(
    db: AsyncSession, assets: list[ProposalAsset]
) -> list[ProposalAssetResponse]:
    if not assets:
        return []
    doc_ids = {a.document_id for a in assets}
    opp_ids = {a.opportunity_id for a in assets if a.opportunity_id}
    docs = {
        d.id: d.name
        for d in (
            await db.execute(select(Document).where(Document.id.in_(doc_ids)))
        )
        .scalars()
        .all()
    }
    opps = {
        o.id: o.name
        for o in (
            await db.execute(select(Opportunity).where(Opportunity.id.in_(opp_ids)))
            if opp_ids
            else await db.execute(select(Opportunity).where(False))
        )
        .scalars()
        .all()
    }
    last_used: dict[uuid.UUID, datetime] = {}
    asset_ids = [a.id for a in assets]
    rows = (
        await db.execute(
            select(
                ProposalAssetUsage.asset_id,
                func.max(ProposalAssetUsage.created_at),
            )
            .where(ProposalAssetUsage.asset_id.in_(asset_ids))
            .group_by(ProposalAssetUsage.asset_id)
        )
    ).all()
    for aid, ts in rows:
        last_used[aid] = ts
    return [
        _to_response(
            a,
            document_name=docs.get(a.document_id),
            opportunity_name=opps.get(a.opportunity_id) if a.opportunity_id else None,
            last_used_at=last_used.get(a.id),
        )
        for a in assets
    ]


async def search_assets(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    params: AssetSearchParams,
    library: str = "all",
) -> list[ProposalAssetResponse]:
    type_filter = LIBRARY_FILTERS.get(library, ASSET_TYPES)
    stmt = (
        select(ProposalAsset)
        .where(ProposalAsset.workspace_id == workspace_id)
        .where(ProposalAsset.asset_type.in_(type_filter))
    )
    if params.asset_type:
        stmt = stmt.where(ProposalAsset.asset_type == params.asset_type)
    if params.agency:
        stmt = stmt.where(
            func.lower(ProposalAsset.agency) == params.agency.lower().strip()
        )
    if params.outcome:
        stmt = stmt.where(ProposalAsset.outcome == params.outcome)
    if params.author:
        stmt = stmt.where(ProposalAsset.author.ilike(f"%{params.author}%"))
    if params.min_win_rate is not None:
        stmt = stmt.where(ProposalAsset.win_rate >= params.min_win_rate)
    if params.date_from:
        stmt = stmt.where(ProposalAsset.submission_date >= params.date_from)
    if params.date_to:
        stmt = stmt.where(ProposalAsset.submission_date <= params.date_to)
    if params.tags:
        stmt = stmt.where(ProposalAsset.tags.overlap(params.tags))

    assets = list(
        (await db.execute(stmt.order_by(desc(ProposalAsset.outcome_weight)).limit(500)))
        .scalars()
        .all()
    )

    if params.q and params.search_mode in ("semantic", "hybrid"):
        from app.llm.router import get_llm_router

        embedder = get_llm_router().embedding_provider()
        vec = (await embedder.embed([params.q])).embeddings[0]
        sql = text(
            """
            SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS score
            FROM proposal_asset
            WHERE workspace_id = :ws AND embedding IS NOT NULL
              AND id = ANY(:ids)
            ORDER BY embedding <=> CAST(:vec AS vector) ASC
            LIMIT :k
            """
        )
        ids = [str(a.id) for a in assets]
        if ids:
            sem_rows = (
                await db.execute(
                    sql,
                    {
                        "vec": _vec_literal(vec),
                        "ws": str(workspace_id),
                        "ids": ids,
                        "k": params.limit,
                    },
                )
            ).all()
            rank = {uuid.UUID(r[0]): float(r[1]) for r in sem_rows}
            assets.sort(
                key=lambda a: rank.get(a.id, 0.0) * (0.6 if params.search_mode == "hybrid" else 1.0)
                + a.outcome_weight * 0.4,
                reverse=True,
            )
    elif params.q:
        q = params.q.lower()
        assets = [
            a
            for a in assets
            if q in a.title.lower() or q in a.summary.lower()
        ]

    page = assets[params.offset : params.offset + params.limit]
    return await enrich_assets(db, page)


async def get_asset_detail(
    db: AsyncSession, *, workspace_id: uuid.UUID, asset_id: uuid.UUID
) -> ProposalAssetDetail | None:
    asset = (
        await db.execute(
            select(ProposalAsset)
            .where(ProposalAsset.id == asset_id)
            .where(ProposalAsset.workspace_id == workspace_id)
            .options(
                selectinload(ProposalAsset.citations),
                selectinload(ProposalAsset.usages),
            )
        )
    ).scalar_one_or_none()
    if asset is None:
        return None
    base = (await enrich_assets(db, [asset]))[0]
    doc = await db.get(Document, asset.document_id)
    citations = [
        AssetCitationResponse(
            id=c.id,
            document_id=c.document_id,
            document_name=doc.name if doc else None,
            chunk_id=c.chunk_id,
            page_start=c.page_start,
            page_end=c.page_end,
            section_path=c.section_path,
            excerpt=c.excerpt,
        )
        for c in asset.citations
    ]
    opp_ids = [u.opportunity_id for u in asset.usages]
    opps = {
        o.id: o
        for o in (
            await db.execute(select(Opportunity).where(Opportunity.id.in_(opp_ids)))
            if opp_ids
            else await db.execute(select(Opportunity).where(False))
        )
        .scalars()
        .all()
    }
    outcomes = {
        po.opportunity_id: po.outcome
        for po in (
            await db.execute(
                select(PursuitOutcome).where(PursuitOutcome.opportunity_id.in_(opp_ids))
            )
            if opp_ids
            else await db.execute(select(PursuitOutcome).where(False))
        )
        .scalars()
        .all()
    }
    usages = [
        AssetUsageResponse(
            opportunity_id=u.opportunity_id,
            opportunity_name=opps[u.opportunity_id].name if u.opportunity_id in opps else None,
            usage_kind=u.usage_kind,
            outcome=outcomes.get(u.opportunity_id),
            created_at=u.created_at,
        )
        for u in asset.usages
    ]
    similar = await similar_assets(db, workspace_id=workspace_id, asset_id=asset_id, top_k=3)
    return ProposalAssetDetail(
        **base.model_dump(),
        citations=citations,
        usages=usages,
        similar_assets=similar,
    )


async def similar_assets(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    asset_id: uuid.UUID,
    top_k: int = 8,
) -> list[ProposalAssetResponse]:
    asset = await db.get(ProposalAsset, asset_id)
    if asset is None or asset.embedding is None:
        return []
    sql = text(
        """
        SELECT id
        FROM proposal_asset
        WHERE workspace_id = :ws AND embedding IS NOT NULL AND id != :aid
        ORDER BY embedding <=> CAST(:vec AS vector) ASC
        LIMIT :k
        """
    )
    rows = (
        await db.execute(
            sql,
            {
                "vec": _vec_literal(asset.embedding),
                "ws": str(workspace_id),
                "aid": str(asset_id),
                "k": top_k,
            },
        )
    ).all()
    ids = [uuid.UUID(r[0]) for r in rows]
    if not ids:
        return []
    found = list(
        (await db.execute(select(ProposalAsset).where(ProposalAsset.id.in_(ids))))
        .scalars()
        .all()
    )
    return await enrich_assets(db, found)


def _pattern(asset: ProposalAsset, pursuits: list[str]) -> AssetPattern:
    return AssetPattern(
        asset_id=asset.id,
        title=asset.title,
        asset_type=asset.asset_type,
        agency=asset.agency,
        wins=asset.wins,
        losses=asset.losses,
        usage_count=asset.usage_count,
        win_rate=asset.win_rate,
        outcome_weight=asset.outcome_weight,
        observation=observation_text(asset.title, asset.wins, asset.losses),
        source_pursuits=pursuits[:6],
    )


async def build_report(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> ProposalIntelligenceReport:
    assets = list(
        (
            await db.execute(
                select(ProposalAsset).where(ProposalAsset.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    pursuits = len(
        {
            u.opportunity_id
            for u in (
                await db.execute(
                    select(ProposalAssetUsage).where(
                        ProposalAssetUsage.workspace_id == workspace_id
                    )
                )
            )
            .scalars()
            .all()
        }
    )
    with_signal = sum(1 for a in assets if a.wins + a.losses > 0)
    decided_rates = [a.win_rate for a in assets if a.win_rate is not None]
    summary = RepositorySummary(
        total_assets=len(assets),
        pursuits_with_assets=pursuits,
        assets_with_outcome_signal=with_signal,
        avg_win_rate=round(sum(decided_rates) / len(decided_rates), 3)
        if decided_rates
        else None,
    )

    async def pursuit_names(asset_id: uuid.UUID) -> list[str]:
        rows = (
            await db.execute(
                select(Opportunity.name)
                .join(
                    ProposalAssetUsage,
                    ProposalAssetUsage.opportunity_id == Opportunity.id,
                )
                .where(ProposalAssetUsage.asset_id == asset_id)
            )
        ).all()
        return [r[0] for r in rows]

    async def top_for(*types: str) -> list[AssetPattern]:
        filtered = [a for a in assets if a.asset_type in types]
        filtered.sort(key=lambda a: (a.outcome_weight, a.usage_count), reverse=True)
        out: list[AssetPattern] = []
        for a in filtered[:8]:
            names = await pursuit_names(a.id)
            out.append(_pattern(a, names))
        return out

    by_agency: dict[str, list[ProposalAsset]] = defaultdict(list)
    for a in assets:
        if a.agency:
            by_agency[a.agency].append(a)

    agency_patterns: list[AssetPattern] = []
    for agency, group in sorted(by_agency.items(), key=lambda x: -len(x[1]))[:6]:
        group.sort(key=lambda a: a.outcome_weight, reverse=True)
        if group:
            names = await pursuit_names(group[0].id)
            agency_patterns.append(_pattern(group[0], names))

    observations: list[str] = []
    for pat in (await top_for("transition_approach"))[:3]:
        if pat.wins + pat.losses >= 2:
            observations.append(
                f"Observed pattern: {pat.title} appeared in {pat.wins} wins and "
                f"{pat.losses} losses across {pat.usage_count} pursuits{'' if pat.win_rate is None else f' ({round(pat.win_rate * 100)}% historical win rate)'}. "
                "Historical correlation only — not causation."
            )

    return ProposalIntelligenceReport(
        summary=summary,
        top_win_themes=await top_for("win_theme", "discriminator"),
        top_transition_approaches=await top_for("transition_approach"),
        top_staffing_approaches=await top_for("staffing_approach", "management_approach"),
        top_executive_summaries=await top_for("executive_summary"),
        agency_patterns=agency_patterns,
        historical_observations=observations,
    )


async def repository_context_for_opportunity(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    agency: str | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Compact proposal repository context for consuming intelligence modules."""
    stmt = select(ProposalAsset).where(ProposalAsset.workspace_id == workspace_id)
    if agency:
        stmt = stmt.where(func.lower(ProposalAsset.agency) == agency.lower().strip())
    assets = list(
        (await db.execute(stmt.order_by(desc(ProposalAsset.outcome_weight)).limit(limit * 2)))
        .scalars()
        .all()
    )
    assets.sort(key=lambda a: a.outcome_weight, reverse=True)
    items = []
    for a in assets[:limit]:
        items.append(
            {
                "asset_type": a.asset_type,
                "title": a.title,
                "summary": a.summary[:400],
                "agency": a.agency,
                "track_record": format_track_record(a.wins, a.losses, a.usage_count),
                "basis": "historical_evidence",
            }
        )
    return {
        "asset_count": len(assets),
        "historical_assets": items,
        "opportunity_id": str(opportunity_id),
    }
