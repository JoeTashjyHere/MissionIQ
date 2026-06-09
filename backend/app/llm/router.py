"""LLM + Embedding routers.

The router picks the first available provider according to MIQ_LLM_PROVIDER_ORDER,
unless a workspace/module override is supplied. Decoupling routing from call sites
is the platform's vendor-agnostic guarantee.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.base import EmbeddingClient, LLMClient
from app.llm.providers.anthropic import AnthropicLLM
from app.llm.providers.azure_openai import AzureOpenAIEmbedder, AzureOpenAILLM
from app.llm.providers.bedrock import BedrockEmbedder, BedrockLLM
from app.llm.providers.local_stub import LocalStubEmbedder, LocalStubLLM
from app.llm.providers.openai import OpenAIEmbedder, OpenAILLM

logger = get_logger(__name__)


def _all_llms() -> dict[str, LLMClient]:
    return {
        "openai": OpenAILLM(),
        "anthropic": AnthropicLLM(),
        "bedrock": BedrockLLM(),
        "azure_openai": AzureOpenAILLM(),
        "local_stub": LocalStubLLM(),
    }


def _all_embedders() -> dict[str, EmbeddingClient]:
    return {
        "openai": OpenAIEmbedder(),
        "azure_openai": AzureOpenAIEmbedder(),
        "bedrock": BedrockEmbedder(),
        "local_stub": LocalStubEmbedder(),
    }


class LLMRouter:
    def __init__(self) -> None:
        self._clients = _all_llms()
        self._embedders = _all_embedders()

    def chat_provider(self, override: str | None = None) -> LLMClient:
        if override:
            client = self._clients.get(override)
            if client and client.is_available():
                return client
            logger.warning("llm.override_unavailable", requested=override)
        order = get_settings().provider_order
        for name in order:
            client = self._clients.get(name)
            if client and client.is_available():
                return client
        # Final guarantee: stub is always available.
        return self._clients["local_stub"]

    def embedding_provider(self) -> EmbeddingClient:
        configured = get_settings().embedding_provider
        client = self._embedders.get(configured)
        if client and client.is_available():
            return client
        logger.warning("embeddings.fallback_to_stub", requested=configured)
        return self._embedders["local_stub"]


@lru_cache
def get_llm_router() -> LLMRouter:
    return LLMRouter()
