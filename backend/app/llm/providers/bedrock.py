"""AWS Bedrock provider stub. Interface-compatible; full impl in Milestone 5."""
from __future__ import annotations

from app.core.config import get_settings
from app.llm.base import EmbeddingResponse, LLMResponse


class BedrockLLM:
    name = "bedrock"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def default_model(self) -> str:
        return self._settings.aws_bedrock_default_model

    def is_available(self) -> bool:
        try:
            import boto3  # noqa: F401
        except ImportError:
            return False
        # Real availability requires AWS creds; defer to actual call.
        return False  # Disabled by default until Milestone 5.

    async def generate_json(  # pragma: no cover
        self, *, system: str, user: str, model: str | None = None, temperature: float = 0.1, max_tokens: int = 2048
    ) -> LLMResponse:
        raise NotImplementedError("Bedrock provider lands in Milestone 5.")


class BedrockEmbedder:
    name = "bedrock"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def default_model(self) -> str:
        return self._settings.aws_bedrock_embedding_model

    @property
    def dimension(self) -> int:
        return self._settings.embedding_dim

    def is_available(self) -> bool:
        return False  # Milestone 5

    async def embed(  # pragma: no cover
        self, texts: list[str], *, model: str | None = None
    ) -> EmbeddingResponse:
        raise NotImplementedError
