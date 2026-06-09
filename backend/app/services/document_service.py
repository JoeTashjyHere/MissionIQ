"""Document upload + processing orchestration."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.ingestion import process_document
from app.models import Document, Opportunity
from app.storage import get_blob_store

_ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


async def upload_document(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    mime_type: str,
    data: bytes,
    doc_type: str,
) -> Document:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise ValidationError("File exceeds maximum upload size.", code="document.too_large")
    if mime_type not in _ALLOWED_MIME and not mime_type.startswith("text/"):
        raise AppError(
            f"Unsupported MIME type: {mime_type}",
            status_code=415,
            code="document.unsupported_type",
        )

    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")

    sha256 = hashlib.sha256(data).hexdigest()
    existing = (
        await db.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.opportunity_id == opportunity_id,
                Document.sha256 == sha256,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    doc_id = uuid.uuid4()
    blob_store = get_blob_store()
    blob_key = await blob_store.write(
        workspace_id=workspace_id,
        document_id=doc_id,
        data=data,
        filename=filename,
    )

    doc = Document(
        id=doc_id,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        name=filename,
        doc_type=doc_type,
        mime_type=mime_type,
        size_bytes=len(data),
        blob_key=blob_key,
        sha256=sha256,
        status="uploaded",
        progress_pct=5,
        stage_started_at=datetime.now(UTC),
        uploaded_by_user_id=user_id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.flush()
    return doc


async def run_pipeline_for(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Run the ingestion pipeline synchronously (FastAPI BackgroundTask wrapper).

    The HTTP request returns immediately; this runs in the background with its
    own session in the API layer (see api/v1/documents.py).
    """
    await process_document(db=db, document_id=document_id)


async def list_documents(
    db: AsyncSession, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .where(Document.opportunity_id == opportunity_id)
        .where(Document.deleted_at.is_(None))
        .order_by(Document.uploaded_at.desc().nullslast())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_document(db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.workspace_id != workspace_id or doc.deleted_at is not None:
        raise NotFoundError("Document not found.", code="document.not_found")
    return doc
