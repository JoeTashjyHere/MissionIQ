"""Reusable schemas: pagination, citations, evidence."""
from __future__ import annotations

import uuid
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    next_cursor: str | None = None
    total_estimate: int | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total_estimate: int | None = None


class DocumentCitation(BaseModel):
    type: Literal["document_chunk"] = "document_chunk"
    id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_start: int | None = None
    page_end: int | None = None
    section_path: str | None = None
    snippet: str


class MarketIntelCitation(BaseModel):
    type: Literal["market_intel_record"] = "market_intel_record"
    id: uuid.UUID
    source_id: str
    external_id: str
    source_url: str | None = None
    title: str


Citation = DocumentCitation | MarketIntelCitation


class Evidence(BaseModel):
    chunk_id: uuid.UUID | None = None
    market_record_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    document_name: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_path: str | None = None
    snippet: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
