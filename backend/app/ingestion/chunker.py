"""Token-bounded chunker with page tracking and ~20% overlap."""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.ingestion.extractors.base import ExtractedPage

_ENCODING = "cl100k_base"
_TARGET_TOKENS = 600
_OVERLAP_TOKENS = 120


@dataclass(slots=True)
class Chunk:
    text: str
    token_count: int
    page_start: int
    page_end: int
    section_path: str | None


def _tokenizer():
    return tiktoken.get_encoding(_ENCODING)


def chunk_pages(pages: list[ExtractedPage]) -> list[Chunk]:
    enc = _tokenizer()
    full_text_parts: list[tuple[str, int, str | None]] = []
    for page in pages:
        if page.text:
            full_text_parts.append((page.text, page.page_number, page.section_path))
    if not full_text_parts:
        return []

    # Tokenize each page; preserve page mapping per token via parallel list.
    token_buf: list[int] = []
    page_buf: list[int] = []
    section_buf: list[str | None] = []
    for text, page_num, section in full_text_parts:
        toks = enc.encode(text)
        if toks:
            token_buf.extend(toks)
            page_buf.extend([page_num] * len(toks))
            section_buf.extend([section] * len(toks))

    chunks: list[Chunk] = []
    i = 0
    n = len(token_buf)
    while i < n:
        end = min(i + _TARGET_TOKENS, n)
        slice_tokens = token_buf[i:end]
        slice_pages = page_buf[i:end]
        slice_sections = section_buf[i:end]
        chunk_text = enc.decode(slice_tokens).strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    text=chunk_text,
                    token_count=len(slice_tokens),
                    page_start=slice_pages[0],
                    page_end=slice_pages[-1],
                    section_path=next((s for s in slice_sections if s), None),
                )
            )
        if end >= n:
            break
        i = end - _OVERLAP_TOKENS
        if i < 0:
            i = 0
    return chunks
