"""DOCX text extractor (python-docx). One synthetic 'page' per paragraph block."""
from __future__ import annotations

import io

from docx import Document as DocxDocument

from app.ingestion.extractors.base import ExtractedPage

# DOCX has no real pages; we synthesize page breaks every N paragraphs to give
# downstream chunking and citations a stable address.
_PARAGRAPHS_PER_SYNTH_PAGE = 25


def extract_docx(data: bytes) -> list[ExtractedPage]:
    doc = DocxDocument(io.BytesIO(data))
    pages: list[ExtractedPage] = []
    buf: list[str] = []
    section_path: str | None = None
    page_num = 1
    paragraph_count = 0
    for para in doc.paragraphs:
        style = (para.style.name if para.style else "") or ""
        text = (para.text or "").strip()
        if style.startswith("Heading"):
            section_path = text or section_path
        if not text:
            continue
        buf.append(text)
        paragraph_count += 1
        if paragraph_count >= _PARAGRAPHS_PER_SYNTH_PAGE:
            pages.append(
                ExtractedPage(
                    page_number=page_num,
                    text="\n".join(buf),
                    section_path=section_path,
                )
            )
            page_num += 1
            buf = []
            paragraph_count = 0
    if buf:
        pages.append(
            ExtractedPage(
                page_number=page_num,
                text="\n".join(buf),
                section_path=section_path,
            )
        )
    return pages or [ExtractedPage(page_number=1, text="", section_path=None)]
