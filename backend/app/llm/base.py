"""LLM + Embedding provider protocols and result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(slots=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    raw: dict = field(default_factory=dict)


@dataclass(slots=True)
class EmbeddingResponse:
    embeddings: list[list[float]]
    provider: str
    model: str
    input_tokens: int = 0
    latency_ms: int = 0


class LLMClient(Protocol):
    name: str

    @property
    def default_model(self) -> str: ...

    def is_available(self) -> bool: ...

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a strict JSON response. Provider must request/coerce JSON output."""


class EmbeddingClient(Protocol):
    name: str

    @property
    def default_model(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def is_available(self) -> bool: ...

    async def embed(self, texts: list[str], *, model: str | None = None) -> EmbeddingResponse: ...
