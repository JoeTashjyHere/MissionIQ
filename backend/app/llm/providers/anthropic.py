"""Anthropic Claude provider. Lazily imports the SDK."""
from __future__ import annotations

import json
import time

from app.core.config import get_settings
from app.llm.base import LLMResponse


class AnthropicLLM:
    name = "anthropic"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def default_model(self) -> str:
        return self._settings.anthropic_default_model

    def is_available(self) -> bool:
        if not self._settings.anthropic_api_key:
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic  # type: ignore

            self._client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
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
        full_system = (
            system
            + "\n\nReturn your response as a single JSON object and nothing else. "
              "Do not include markdown fences."
        )
        resp = await client.messages.create(
            model=model or self.default_model,
            system=full_system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        text_parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "".join(text_parts).strip()
        # Strip code fences defensively
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
        # Best-effort validate it parses
        try:
            json.loads(text)
        except Exception:
            text = "{}"
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=resp.model,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
