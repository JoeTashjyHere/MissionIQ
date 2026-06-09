"""Document schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.document import DOC_STATUSES, DOC_TYPES
from app.schemas.common import ORMModel

DocType = Literal[*DOC_TYPES]  # type: ignore[valid-type]
DocStatus = Literal[*DOC_STATUSES]  # type: ignore[valid-type]


class DocumentResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    name: str
    doc_type: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    status: str
    error_message: str | None
    uploaded_at: datetime | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    page_start: int | None
    page_end: int | None
    section_path: str | None
    text: str
    token_count: int
    embedding_model: str | None


class DocumentList(BaseModel):
    items: list[DocumentResponse]
