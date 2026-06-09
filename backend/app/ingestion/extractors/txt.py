"""Plain text extractor. Splits on form-feeds, or every 3000 chars."""
from __future__ import annotations

from app.ingestion.extractors.base import ExtractedPage

_CHARS_PER_SYNTH_PAGE = 3000


def extract_txt(data: bytes) -> list[ExtractedPage]:
    text = data.decode("utf-8", errors="replace")
    if "\f" in text:
        chunks = text.split("\f")
    else:
        chunks = [text[i : i + _CHARS_PER_SYNTH_PAGE] for i in range(0, len(text), _CHARS_PER_SYNTH_PAGE)] or [""]
    return [
        ExtractedPage(page_number=i + 1, text=chunk.strip())
        for i, chunk in enumerate(chunks)
    ]
