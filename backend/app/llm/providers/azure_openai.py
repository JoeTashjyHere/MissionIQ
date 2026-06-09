"""Azure OpenAI provider. Uses the same openai SDK with Azure config."""
from __future__ import annotations

import time

from app.core.config import get_settings
from app.llm.base import EmbeddingResponse, LLMResponse


class AzureOpenAILLM:
    name = "azure_openai"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def default_model(self) -> str:
        return self._settings.azure_openai_chat_deployment or "gpt-4o"

    def is_available(self) -> bool:
        s = self._settings
        if not (s.azure_openai_endpoint and s.azure_openai_api_key and s.azure_openai_chat_deployment):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from openai import AsyncAzureOpenAI  # type: ignore

            s = self._settings
            self._client = AsyncAzureOpenAI(
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
                azure_endpoint=s.azure_openai_endpoint,
            )
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
        deployment = model or self._settings.azure_openai_chat_deployment
        start = time.perf_counter()
        resp = await client.chat.completions.create(
            model=deployment,
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
            model=deployment,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )


class AzureOpenAIEmbedder:
    name = "azure_openai"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def default_model(self) -> str:
        return self._settings.azure_openai_embedding_deployment or "text-embedding-3-small"

    @property
    def dimension(self) -> int:
        return self._settings.embedding_dim

    def is_available(self) -> bool:
        s = self._settings
        if not (s.azure_openai_endpoint and s.azure_openai_api_key and s.azure_openai_embedding_deployment):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from openai import AsyncAzureOpenAI  # type: ignore

            s = self._settings
            self._client = AsyncAzureOpenAI(
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
                azure_endpoint=s.azure_openai_endpoint,
            )
        return self._client

    async def embed(self, texts: list[str], *, model: str | None = None) -> EmbeddingResponse:
        client = self._ensure_client()
        deployment = model or self._settings.azure_openai_embedding_deployment
        start = time.perf_counter()
        resp = await client.embeddings.create(model=deployment, input=texts)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return EmbeddingResponse(
            embeddings=[list(item.embedding) for item in resp.data],
            provider=self.name,
            model=deployment,
            input_tokens=getattr(getattr(resp, "usage", None), "prompt_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
