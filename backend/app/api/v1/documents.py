"""Document upload + processing + retrieval endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Path,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, session_scope
from app.core.dependencies import CurrentUser, OppScope, WorkspaceScope
from app.core.errors import NotFoundError
from app.ingestion import process_document
from app.models import Document
from app.schemas.document import DocumentResponse, DocType
from app.services import document_service
from app.services.audit_service import write_audit
from app.storage import get_blob_store

router = APIRouter()


async def _process_in_background(document_id: uuid.UUID) -> None:
    """Background task: open a fresh session and run the ingestion pipeline."""
    async with session_scope() as db:
        await process_document(db=db, document_id=document_id)


@router.post(
    "/opportunities/{opportunity_id}/documents",
    response_model=DocumentResponse,
    status_code=202,
)
async def upload_doc(
    background: BackgroundTasks,
    scope: OppScope,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[DocType, Form()] = "other",
) -> DocumentResponse:
    ws, _, opportunity_id = scope
    data = await file.read()
    doc = await document_service.upload_document(
        db,
        workspace_id=ws.id,
        opportunity_id=opportunity_id,
        user_id=user.id,
        filename=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        data=data,
        doc_type=doc_type,
    )
    await write_audit(
        db,
        action="document.uploaded",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="document",
        target_id=doc.id,
        meta={
            "name": doc.name,
            "doc_type": doc.doc_type,
            "size_bytes": doc.size_bytes,
        },
    )
    background.add_task(_process_in_background, doc.id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/opportunities/{opportunity_id}/documents", response_model=list[DocumentResponse]
)
async def list_docs(
    scope: OppScope, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[DocumentResponse]:
    ws, _, opportunity_id = scope
    items = await document_service.list_documents(db, ws.id, opportunity_id)
    return [DocumentResponse.model_validate(d) for d in items]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_doc(
    document_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    doc = await db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise NotFoundError("Document not found.", code="document.not_found")
    # Verify access via workspace membership
    from sqlalchemy import select
    from app.models import TeamMember

    member = (
        await db.execute(
            select(TeamMember).where(
                TeamMember.workspace_id == doc.workspace_id,
                TeamMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise NotFoundError("Document not found.", code="document.not_found")
    return DocumentResponse.model_validate(doc)


@router.get("/documents/{document_id}/raw")
async def download_doc(
    document_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    doc_resp = await get_doc(document_id, user, db)
    doc = await db.get(Document, doc_resp.id)
    blob = await get_blob_store().read(workspace_id=doc.workspace_id, key=doc.blob_key)

    def _gen():
        yield blob

    return StreamingResponse(
        _gen(),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{doc.name}"'},
    )


@router.post("/documents/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_doc(
    document_id: Annotated[uuid.UUID, Path()],
    background: BackgroundTasks,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    doc_resp = await get_doc(document_id, user, db)
    background.add_task(_process_in_background, doc_resp.id)
    return doc_resp
