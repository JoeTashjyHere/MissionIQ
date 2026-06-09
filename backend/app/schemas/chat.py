"""Chat schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Citation, ORMModel


class ChatThreadCreate(BaseModel):
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    title: str | None = None


class ChatThreadResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    title: str | None
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageResponse(ORMModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: Literal["user", "assistant", "system"]
    content: str
    citations: list[Citation] = []
    status: Literal["ok", "insufficient_context", "error"] = "ok"
    model_provider: str | None
    model_name: str | None
    created_at: datetime


class ChatSendResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
