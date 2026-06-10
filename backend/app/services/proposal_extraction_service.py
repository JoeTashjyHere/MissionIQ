"""Proposal asset extraction — decompose proposal documents into reusable intelligence.

Triggered after document ingestion (proposal doc types) or manually via API.
Uses the existing LLM + prompt library; writes structured assets, never
replacing the source document.
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.graph.extract import FactBundle
from app.graph import service as graph_service
from app.graph.service import opportunity_meta
from app.llm.prompt_library import PromptLibrary
from app.llm.router import get_llm_router
from app.models import Document, DocumentChunk, Opportunity, ProposalAsset, PursuitOutcome
from app.models.proposal_asset import PROPOSAL_DOC_TYPES
from app.schemas.proposal_repository import ProposalExtractionOutput
from app.services.audit_service import write_audit
from app.services.proposal_graph import build_graph_bundle, extraction_module_id
from app.services.proposal_repository_service import (
    asset_normalized_key,
    recompute_asset_outcomes,
    sync_asset_outcomes_from_opportunity,
)

logger = logging.getLogger(__name__)

_PROMPT_ID = "proposal.extract_assets"
_PROMPT_VERSION = "v1"


def should_extract(doc: Document) -> bool:
    return doc.doc_type in PROPOSAL_DOC_TYPES


async def extract_proposal_assets(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    actor_user_id: uuid.UUID | None = None,
) -> list[ProposalAsset]:
    doc = await db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("Document not found.", code="document.not_found")
    if doc.status != "ready":
        raise ConflictError(
            "Document must be fully indexed before extraction.",
            code="proposal.document_not_ready",
        )

    chunks = list(
        (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc.id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        )
        .scalars()
        .all()
    )
    opp: Opportunity | None = None
    if doc.opportunity_id:
        opp = await db.get(Opportunity, doc.opportunity_id)

    outcome = None
    if opp:
        po = (
            await db.execute(
                select(PursuitOutcome).where(PursuitOutcome.opportunity_id == opp.id)
            )
        ).scalar_one_or_none()
        outcome = po.outcome if po else None

    prompts = PromptLibrary()
    evidence = [
        {
            "chunk_index": c.chunk_index,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "section_path": c.section_path,
            "text": c.text[:2500],
        }
        for c in chunks[:40]
    ]
    system, user, _ = prompts.render(
        _PROMPT_ID,
        _PROMPT_VERSION,
        document={
            "name": doc.name,
            "doc_type": doc.doc_type,
            "page_count": doc.page_count,
            "chunk_count": doc.chunk_count,
        },
        opportunity={
            "name": opp.name if opp else None,
            "agency": opp.agency if opp else None,
            "customer": opp.sub_agency if opp else None,
        },
        evidence=evidence,
    )

    llm = get_llm_router().chat_provider()
    llm_resp = await llm.generate_json(system=system, user=user)
    try:
        raw = json.loads(llm_resp.text)
    except json.JSONDecodeError:
        raw = {"assets": [], "inputs_missing": ["model returned non-JSON output"]}

    parsed = ProposalExtractionOutput.model_validate(raw)
    embedder = get_llm_router().embedding_provider()
    model_tag = f"{embedder.provider}:{embedder.model}"

    # Re-extract replaces prior assets from this document.
    await db.execute(delete(ProposalAsset).where(ProposalAsset.document_id == doc.id))

    created: list[ProposalAsset] = []
    merged_bundle = FactBundle()
    for item in parsed.assets:
        text_for_embed = f"{item.title}\n{item.summary}"
        emb = (await embedder.embed([text_for_embed])).embeddings[0]
        asset = ProposalAsset(
            workspace_id=doc.workspace_id,
            asset_type=item.asset_type,
            title=item.title,
            summary=item.summary,
            content=item.content,
            document_id=doc.id,
            opportunity_id=doc.opportunity_id,
            agency=opp.agency if opp else None,
            customer_name=opp.sub_agency if opp else None,
            outcome=outcome,
            source_type=doc.source_type,
            source_connector_id=doc.source_connector_id,
            source_external_id=doc.source_external_id,
            tags=item.tags or None,
            extraction_confidence=item.confidence,
            extraction_basis=item.basis,
            embedding=emb,
            embedding_model=model_tag,
            normalized_key=asset_normalized_key(item.asset_type, item.title),
        )
        db.add(asset)
        await db.flush()

        from app.models.proposal_asset import ProposalAssetCitation, ProposalAssetUsage

        for cite in item.citations:
            db.add(
                ProposalAssetCitation(
                    asset_id=asset.id,
                    document_id=doc.id,
                    page_start=cite.page_start,
                    page_end=cite.page_end,
                    section_path=cite.section_path,
                    excerpt=cite.excerpt[:4000],
                )
            )
        if doc.opportunity_id:
            db.add(
                ProposalAssetUsage(
                    workspace_id=doc.workspace_id,
                    asset_id=asset.id,
                    opportunity_id=doc.opportunity_id,
                    usage_kind="extracted_from",
                )
            )
        created.append(asset)

        if opp:
            bundle = build_graph_bundle(
                asset_title=item.title,
                asset_type=item.asset_type,
                agency=opp.agency,
                opportunity=opportunity_meta(opp),
                capabilities=item.tags,
            )
            merged_bundle.extend(bundle)

    if opp and merged_bundle.edges:
        try:
            await graph_service.ingest_proposal_bundle(
                db,
                workspace_id=doc.workspace_id,
                opportunity_id=opp.id,
                module_id=extraction_module_id(),
                bundle=merged_bundle,
            )
        except Exception:  # noqa: BLE001
            logger.exception("graph ingest failed for proposal extraction on %s", doc.id)

    if doc.opportunity_id:
        await sync_asset_outcomes_from_opportunity(db, opportunity_id=doc.opportunity_id)
    else:
        await recompute_asset_outcomes(db, workspace_id=doc.workspace_id)

    await write_audit(
        db,
        action="proposal_asset.extracted",
        workspace_id=doc.workspace_id,
        actor_user_id=actor_user_id,
        target_type="document",
        target_id=doc.id,
        meta={"asset_count": len(created), "document_name": doc.name},
    )
    await db.flush()
    return created
