"""OpenAI provider. Lazily imports the SDK so the platform runs without it."""
from __future__ import annotations

import time

from app.core.config import get_settings
from app.llm.base import EmbeddingResponse, LLMResponse


class OpenAILLM:
    name = "openai"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def default_model(self) -> str:
        return self._settings.openai_default_model

    def is_available(self) -> bool:
        s = self._settings
        if not s.openai_api_key:
            return False
        if not s.openai_training_opt_out_ack:
            return False
        try:  # noqa: SIM105
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from openai import AsyncOpenAI  # type: ignore

            self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        return self._client

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        client = self._ensure_client()
        start = time.perf_counter()
        resp = await client.chat.completions.create(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        text = resp.choices[0].message.content or "{}"
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=resp.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )


class OpenAIEmbedder:
    name = "openai"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def default_model(self) -> str:
        return self._settings.openai_embedding_model

    @property
    def dimension(self) -> int:
        return self._settings.embedding_dim

    def is_available(self) -> bool:
        s = self._settings
        if not s.openai_api_key:
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from openai import AsyncOpenAI  # type: ignore

            self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        return self._client

    async def embed(self, texts: list[str], *, model: str | None = None) -> EmbeddingResponse:
        client = self._ensure_client()
        start = time.perf_counter()
        resp = await client.embeddings.create(
            model=model or self.default_model,
            input=texts,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        embeddings = [list(item.embedding) for item in resp.data]
        usage = getattr(resp, "usage", None)
        return EmbeddingResponse(
            embeddings=embeddings,
            provider=self.name,
            model=resp.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
