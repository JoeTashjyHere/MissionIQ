"""Orchestrates: extract → chunk → embed → persist."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.chunker import chunk_pages
from app.ingestion.extractors.base import extract
from app.llm.router import get_llm_router
from app.models import Document, DocumentChunk
from app.storage import get_blob_store

logger = get_logger(__name__)


async def process_document(*, db: AsyncSession, document_id: uuid.UUID) -> None:
    """Run the pipeline synchronously. Caller commits the session."""
    doc = await db.get(Document, document_id)
    if doc is None:
        logger.warning("ingestion.document_missing", document_id=str(document_id))
        return

    doc.status = "extracting"
    await db.flush()

    try:
        blob_store = get_blob_store()
        data = await blob_store.read(workspace_id=doc.workspace_id, key=doc.blob_key)
        pages = extract(filename=doc.name, mime_type=doc.mime_type, data=data)
        doc.page_count = len(pages)

        doc.status = "chunking"
        await db.flush()
        chunks = chunk_pages(pages)

        # Replace any existing chunks (re-process safety)
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

        doc.status = "embedding"
        await db.flush()
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

        doc.status = "ready"
        doc.processed_at = datetime.now(UTC)
        doc.error_message = None
        await db.flush()
        logger.info(
            "ingestion.complete",
            document_id=str(doc.id),
            pages=doc.page_count,
            chunks=len(chunks),
        )
    except Exception as exc:  # noqa: BLE001
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]
        await db.flush()
        logger.exception("ingestion.failed", document_id=str(doc.id))
