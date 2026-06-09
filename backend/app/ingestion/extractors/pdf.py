"""PDF text extractor (pypdf)."""
from __future__ import annotations

import io

from pypdf import PdfReader

from app.ingestion.extractors.base import ExtractedPage


def extract_pdf(data: bytes) -> list[ExtractedPage]:
    reader = PdfReader(io.BytesIO(data))
    pages: list[ExtractedPage] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(ExtractedPage(page_number=i, text=text.strip()))
    return pages
