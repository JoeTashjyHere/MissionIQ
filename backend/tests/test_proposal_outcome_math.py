"""Proposal asset outcome statistics — observed patterns only."""
from __future__ import annotations

import uuid

import pytest

from app.services.proposal_repository_service import (
    asset_normalized_key,
    compute_asset_outcome_stats,
    format_track_record,
)


def test_compute_asset_outcome_stats_dedupes_by_opportunity():
    opp_a = uuid.uuid4()
    opp_b = uuid.uuid4()
    wins, losses, usage, rate, weight = compute_asset_outcome_stats(
        [
            (opp_a, "won"),
            (opp_a, "won"),  # duplicate usage row → one pursuit
            (opp_b, "lost"),
        ]
    )
    assert usage == 2
    assert wins == 1
    assert losses == 1
    assert rate == pytest.approx(0.5)
    assert weight == pytest.approx(0.5)


def test_format_track_record_includes_usage_and_rate():
    text = format_track_record(3, 1, 5)
    assert text is not None
    assert "5 pursuit" in text
    assert "3W" in text
    assert "1L" in text
    assert "75%" in text


def test_asset_normalized_key_is_stable():
    k1 = asset_normalized_key("win_theme", "Mission Continuity")
    k2 = asset_normalized_key("win_theme", "mission continuity")
    assert k1 == k2
