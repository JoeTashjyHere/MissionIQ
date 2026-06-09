"""LLM router falls back to local_stub when no real provider is configured."""
from __future__ import annotations

import json

import pytest

from app.llm.router import LLMRouter


def test_router_picks_local_stub_when_no_keys():
    router = LLMRouter()
    client = router.chat_provider()
    assert client.is_available()
    assert client.name in ("local_stub", "openai", "anthropic", "azure_openai")


@pytest.mark.asyncio
async def test_stub_returns_json_with_notice():
    router = LLMRouter()
    client = router.chat_provider("local_stub")
    resp = await client.generate_json(
        system="You are an analyst.",
        user="Generate an opportunity_summary for a federal RFP.",
    )
    payload = json.loads(resp.text)
    assert payload.get("__stub__") is True
    assert "executive_summary" in payload


@pytest.mark.asyncio
async def test_embedder_dim_matches_settings():
    router = LLMRouter()
    embedder = router.embedding_provider()
    resp = await embedder.embed(["hello world", "second text"])
    assert len(resp.embeddings) == 2
    assert all(len(v) == embedder.dimension for v in resp.embeddings)
