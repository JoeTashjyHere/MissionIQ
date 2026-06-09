"""Retrieval-augmented generation engine.

Workspace-scoped vector search over ``document_chunk.embedding`` using pgvector
cosine similarity. Returns ``Evidence`` records that downstream prompts and
citations consume.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.router import LLMRouter
from app.models import Document, DocumentChunk, MarketIntelRecord


@dataclass(slots=True)
class Evidence:
    chunk_id: uuid.UUID | None
    market_record_id: uuid.UUID | None
    document_id: uuid.UUID | None
    document_name: str | None
    page_start: int | None
    page_end: int | None
    section_path: str | None
    snippet: str
    score: float


class RAGEngine:
    def __init__(self, db: AsyncSession, llm_router: LLMRouter) -> None:
        self.db = db
        self.llm_router = llm_router

    async def _embed(self, query: str) -> list[float]:
        embedder = self.llm_router.embedding_provider()
        resp = await embedder.embed([query])
        return resp.embeddings[0]

    async def retrieve(
        self,
        *,
        query: str,
        workspace_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        top_k: int = 12,
    ) -> list[Evidence]:
        vec = await self._embed(query)
        sql = text(
            """
            SELECT c.id AS chunk_id,
                   c.document_id,
                   c.page_start,
                   c.page_end,
                   c.section_path,
                   c.text,
                   d.name AS document_name,
                   1 - (c.embedding <=> CAST(:vec AS vector)) AS score
            FROM document_chunk c
            JOIN document d ON d.id = c.document_id
            WHERE c.workspace_id = :ws
              AND c.opportunity_id = :opp
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:vec AS vector) ASC
            LIMIT :k
            """
        )
        result = await self.db.execute(
            sql,
            {
                "vec": _vec_literal(vec),
                "ws": str(workspace_id),
                "opp": str(opportunity_id),
                "k": top_k,
            },
        )
        rows = result.mappings().all()
        items: list[Evidence] = []
        for r in rows:
            snippet = r["text"]
            if len(snippet) > 1200:
                snippet = snippet[:1200] + "…"
            items.append(
                Evidence(
                    chunk_id=r["chunk_id"],
                    market_record_id=None,
                    document_id=r["document_id"],
                    document_name=r["document_name"],
                    page_start=r["page_start"],
                    page_end=r["page_end"],
                    section_path=r["section_path"],
                    snippet=snippet,
                    score=float(r["score"]) if r["score"] is not None else 0.0,
                )
            )
        return items

    async def retrieve_market(
        self,
        *,
        query: str,
        workspace_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        top_k: int = 4,
    ) -> list[Evidence]:
        """Return market-intel evidence linked to this opportunity (no vector
        ranking in MVP — vector ranking activates when summary embeddings exist).
        """
        from app.models import OpportunityMarketIntelLink

        stmt = (
            select(MarketIntelRecord, OpportunityMarketIntelLink)
            .join(
                OpportunityMarketIntelLink,
                OpportunityMarketIntelLink.market_intel_record_id == MarketIntelRecord.id,
            )
            .where(OpportunityMarketIntelLink.opportunity_id == opportunity_id)
            .where(OpportunityMarketIntelLink.workspace_id == workspace_id)
            .limit(top_k)
        )
        result = await self.db.execute(stmt)
        items: list[Evidence] = []
        for rec, _link in result.all():
            snippet = rec.summary or rec.title
            items.append(
                Evidence(
                    chunk_id=None,
                    market_record_id=rec.id,
                    document_id=None,
                    document_name=rec.title,
                    page_start=None,
                    page_end=None,
                    section_path=rec.source_id,
                    snippet=snippet,
                    score=1.0,
                )
            )
        return items


def _vec_literal(v: list[float]) -> str:
    """Render a Python list as a pgvector literal '[1,2,3]'."""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
