"""Build serializable citations from RAG evidence."""
from __future__ import annotations

from app.intelligence.rag import Evidence
from app.schemas.common import Citation, DocumentCitation, MarketIntelCitation


def build_citations(
    evidence: list[Evidence],
    market_evidence: list[Evidence],
) -> list[Citation]:
    out: list[Citation] = []
    for ev in evidence:
        if ev.chunk_id and ev.document_id and ev.document_name:
            out.append(
                DocumentCitation(
                    id=ev.chunk_id,
                    document_id=ev.document_id,
                    document_name=ev.document_name,
                    page_start=ev.page_start,
                    page_end=ev.page_end,
                    section_path=ev.section_path,
                    snippet=ev.snippet[:600],
                )
            )
    for mi in market_evidence:
        if mi.market_record_id:
            out.append(
                MarketIntelCitation(
                    id=mi.market_record_id,
                    source_id=mi.section_path or "unknown",
                    external_id=str(mi.market_record_id),
                    source_url=None,
                    title=mi.document_name or "(market record)",
                )
            )
    return out
