"""Dispatch text extraction by filename / MIME."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import AppError


@dataclass(slots=True)
class ExtractedPage:
    page_number: int  # 1-indexed
    text: str
    section_path: str | None = None


def extract(*, filename: str, mime_type: str, data: bytes) -> list[ExtractedPage]:
    name = filename.lower()
    if name.endswith(".pdf") or mime_type == "application/pdf":
        from app.ingestion.extractors.pdf import extract_pdf

        return extract_pdf(data)
    if name.endswith(".docx") or mime_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        from app.ingestion.extractors.docx import extract_docx

        return extract_docx(data)
    if name.endswith(".txt") or mime_type.startswith("text/"):
        from app.ingestion.extractors.txt import extract_txt

        return extract_txt(data)
    raise AppError(
        f"Unsupported document type: {mime_type} ({filename})",
        status_code=415,
        code="document.unsupported_type",
    )
