"""Outcome Intelligence schemas.

Epistemic honesty contract for everything in this file: the workspace-level
analysis is deterministic statistics. Patterns are *observed*, correlations
are *historical*, and every item carries its supporting evidence (the source
pursuits). Nothing here asserts causation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.outcome import OUTCOMES, RECOMMENDATION_TYPES
from app.schemas.common import ORMModel

Outcome = Literal[*OUTCOMES]  # type: ignore[valid-type]
RecommendationType = Literal[*RECOMMENDATION_TYPES]  # type: ignore[valid-type]


# ── Outcome capture ─────────────────────────────────────────────────────────


class OutcomeRecordRequest(BaseModel):
    outcome: Outcome
    decided_at: datetime | None = None
    awarded_value_cents: int | None = Field(default=None, ge=0)
    awarded_to_competitor: str | None = None
    outcome_factors: list[str] = []
    debrief_notes: str | None = None


class RecommendationOutcomeResponse(ORMModel):
    id: uuid.UUID
    module_id: str
    recommendation_type: str
    predicted_label: str | None
    predicted_score: float | None
    aligned: bool | None
    ai_output_id: uuid.UUID | None


class PursuitOutcomeResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    outcome: str
    decided_at: datetime | None
    awarded_value_cents: int | None
    awarded_to_competitor: str | None
    outcome_factors: list[str] | None
    debrief_notes: str | None
    created_at: datetime
    updated_at: datetime
    # Denormalized for list views.
    opportunity_name: str | None = None
    agency: str | None = None
    recommendation_outcomes: list[RecommendationOutcomeResponse] = []


# ── Workspace analysis (deterministic) ──────────────────────────────────────


class SourcePursuit(BaseModel):
    id: uuid.UUID
    name: str
    outcome: str


class OutcomePattern(BaseModel):
    """An observed pattern: an entity's track record across decided pursuits.
    ``observation`` is descriptive ("Appeared in 3 won and 1 lost pursuits"),
    never causal."""

    label: str
    entity_type: str
    wins: int
    losses: int
    win_rate: float | None
    outcome_weight: float
    observation: str
    decided_value_cents: int | None = None
    # Competitor trends only: losses where this competitor took the award.
    awards_taken: int | None = None
    source_pursuits: list[SourcePursuit] = []


class FactorFrequency(BaseModel):
    """Debrief factor counts across recorded outcomes."""

    factor: str
    in_wins: int
    in_losses: int


class RecommendationPerformance(BaseModel):
    """Alignment between a recommendation type and recorded outcomes — a
    historical correlation, not a measure of causal accuracy."""

    recommendation_type: str
    module_id: str
    total: int
    aligned: int
    alignment_rate: float | None


class CalibrationBucket(BaseModel):
    range_label: str  # e.g. "60–80"
    predictions: int
    observed_wins: int
    observed_win_rate: float | None
    avg_predicted_score: float | None


class StrategicObservation(BaseModel):
    observation: str
    kind: Literal["observed_pattern", "historical_correlation"]
    sources: list[str] = []


class OutcomeSummary(BaseModel):
    recorded: int
    decided: int
    wins: int
    losses: int
    win_rate: float | None
    no_bids: int
    value_won_cents: int
    recommendation_alignment_rate: float | None


class OutcomeIntelligenceReport(BaseModel):
    summary: OutcomeSummary
    win_patterns: list[OutcomePattern]
    loss_patterns: list[OutcomePattern]
    factor_frequencies: list[FactorFrequency]
    agency_trends: list[OutcomePattern]
    capability_trends: list[OutcomePattern]
    competitor_trends: list[OutcomePattern]
    recommendation_performance: list[RecommendationPerformance]
    calibration: list[CalibrationBucket]
    strategic_observations: list[StrategicObservation]
