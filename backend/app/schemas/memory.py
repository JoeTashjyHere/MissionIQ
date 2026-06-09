"""Schemas for the Memory + Knowledge Graph layer.

Every surfaced item carries a ``basis`` so a capture lead can tell apart:

- ``historical``  — drawn from PRIOR opportunities in the graph
- ``current``     — observed on THIS opportunity
- ``inference``   — an aggregated judgment MissionIQ synthesized
"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

MemoryBasis = Literal["historical", "current", "inference"]


class SourceOpportunity(BaseModel):
    id: uuid.UUID
    name: str


class MemoryItem(BaseModel):
    label: str
    basis: MemoryBasis
    entity_type: str | None = None
    detail: str | None = None
    frequency: int = 1  # number of opportunities referencing this item
    source_opportunities: list[SourceOpportunity] = []
    attributes: dict = {}


class SimilarOpportunity(BaseModel):
    opportunity_id: uuid.UUID
    name: str
    agency: str | None = None
    score: float
    reasons: list[str] = []
    shared_entities: int = 0


class AgencyIntelligence(BaseModel):
    agency: str | None = None
    mission: str | None = None
    strategic_goals: list[str] = []
    opportunities_count: int = 0
    recurring_risks: list[MemoryItem] = []
    recurring_win_themes: list[MemoryItem] = []
    known_competitors: list[MemoryItem] = []


class PursuitMemory(BaseModel):
    opportunity_id: uuid.UUID
    opportunity_name: str
    has_history: bool
    summary: str
    similar_opportunities: list[SimilarOpportunity] = []
    prior_risks: list[MemoryItem] = []
    prior_discriminators: list[MemoryItem] = []
    prior_win_themes: list[MemoryItem] = []
    agency_intelligence: AgencyIntelligence | None = None
    inferences: list[str] = []
    graph_stats: dict[str, int] = {}


class HistoricalInsightRepository(BaseModel):
    win_themes: list[MemoryItem] = []
    discriminators: list[MemoryItem] = []
    risks: list[MemoryItem] = []
    competitors: list[MemoryItem] = []
    graph_stats: dict[str, int] = {}
