"""Chunker preserves page numbers and produces overlapping windows."""
from __future__ import annotations

from app.ingestion.chunker import chunk_pages
from app.ingestion.extractors.base import ExtractedPage


def test_chunker_handles_empty_input():
    assert chunk_pages([]) == []


def test_chunker_splits_long_text_and_tracks_pages():
    page_text = " ".join([f"word{i}" for i in range(800)])
    pages = [
        ExtractedPage(page_number=1, text=page_text),
        ExtractedPage(page_number=2, text=page_text),
        ExtractedPage(page_number=3, text=page_text),
    ]
    chunks = chunk_pages(pages)
    assert len(chunks) > 1
    for c in chunks:
        assert 1 <= c.page_start <= 3
        assert 1 <= c.page_end <= 3
        assert c.page_end >= c.page_start
        assert c.token_count > 0


def test_chunker_carries_section_path():
    pages = [ExtractedPage(page_number=1, text="hello world", section_path="Section L.3.1")]
    chunks = chunk_pages(pages)
    assert chunks
    assert chunks[0].section_path == "Section L.3.1"
