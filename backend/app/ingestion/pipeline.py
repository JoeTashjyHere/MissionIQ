"""Orchestrates: extract → chunk → embed → persist.

Each transition is reflected in ``document.status`` + ``document.progress_pct``
and written to the audit log, so the UI can show a live, executive-grade
progress experience and security teams can replay exactly what happened to
every uploaded artifact.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.chunker import chunk_pages
from app.ingestion.extractors.base import extract
from app.llm.router import get_llm_router
from app.models import Document, DocumentChunk
from app.models.document import DOC_STATUS_PROGRESS
from app.services.audit_service import write_audit
from app.storage import get_blob_store

logger = get_logger(__name__)


async def _advance(
    db: AsyncSession,
    doc: Document,
    status: str,
    *,
    meta: dict | None = None,
) -> None:
    """Update document status, progress, and audit log for a stage transition."""
    doc.status = status
    doc.progress_pct = DOC_STATUS_PROGRESS.get(status, doc.progress_pct)
    doc.stage_started_at = datetime.now(UTC)
    await db.flush()
    await write_audit(
        db,
        action=f"document.processing.{status}",
        workspace_id=doc.workspace_id,
        actor_user_id=doc.uploaded_by_user_id,
        target_type="document",
        target_id=doc.id,
        meta={
            "name": doc.name,
            "doc_type": doc.doc_type,
            "progress_pct": doc.progress_pct,
            **(meta or {}),
        },
    )


async def process_document(*, db: AsyncSession, document_id: uuid.UUID) -> None:
    """Run the pipeline synchronously. Caller commits the session."""
    doc = await db.get(Document, document_id)
    if doc is None:
        logger.warning("ingestion.document_missing", document_id=str(document_id))
        return

    try:
        await _advance(db, doc, "parsing")
        blob_store = get_blob_store()
        data = await blob_store.read(workspace_id=doc.workspace_id, key=doc.blob_key)
        pages = extract(filename=doc.name, mime_type=doc.mime_type, data=data)
        doc.page_count = len(pages)

        await _advance(db, doc, "chunking", meta={"pages": len(pages)})
        chunks = chunk_pages(pages)

        # Replace any existing chunks (re-process safety)
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

        await _advance(db, doc, "embedding", meta={"chunks": len(chunks)})
        model_tag: str | None = None
        if chunks:
            embedder = get_llm_router().embedding_provider()
            texts = [c.text for c in chunks]
            emb_resp = await embedder.embed(texts)
            model_tag = f"{emb_resp.provider}:{emb_resp.model}"
            for idx, (c, vec) in enumerate(zip(chunks, emb_resp.embeddings, strict=False)):
                db.add(
                    DocumentChunk(
                        workspace_id=doc.workspace_id,
                        document_id=doc.id,
                        opportunity_id=doc.opportunity_id,
                        chunk_index=idx,
                        page_start=c.page_start,
                        page_end=c.page_end,
                        section_path=c.section_path,
                        text=c.text,
                        token_count=c.token_count,
                        embedding=vec,
                        embedding_model=model_tag,
                    )
                )
        doc.chunk_count = len(chunks)
        doc.processed_at = datetime.now(UTC)
        doc.error_message = None

        await _advance(
            db,
            doc,
            "ready",
            meta={
                "pages": doc.page_count,
                "chunks": len(chunks),
                "embedding_model": model_tag,
            },
        )
        logger.info(
            "ingestion.complete",
            document_id=str(doc.id),
            pages=doc.page_count,
            chunks=len(chunks),
        )
    except Exception as exc:  # noqa: BLE001
        doc.status = "failed"
        doc.progress_pct = DOC_STATUS_PROGRESS["failed"]
        doc.error_message = str(exc)[:1000]
        await db.flush()
        await write_audit(
            db,
            action="document.processing.failed",
            workspace_id=doc.workspace_id,
            actor_user_id=doc.uploaded_by_user_id,
            target_type="document",
            target_id=doc.id,
            meta={"error": doc.error_message, "name": doc.name},
        )
        logger.exception("ingestion.failed", document_id=str(doc.id))
