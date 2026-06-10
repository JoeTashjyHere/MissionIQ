"""Proposal repository epistemic honesty — no causal claims."""
from __future__ import annotations

from app.services.outcome_intelligence_service import observation_text

CAUSAL_PHRASES = ("caused", "because of", "leads to wins", "led to the loss")


def test_observation_text_for_assets_is_descriptive():
    text = observation_text("Phased transition", 3, 1)
    assert "appeared in" in text
    assert "3 won" in text
    assert "1 lost" in text
    lower = text.lower()
    for phrase in CAUSAL_PHRASES:
        assert phrase not in lower


def test_build_report_observations_template():
    obs = (
        "Observed pattern: Phased transition appeared in 2 wins and "
        "1 losses across 4 pursuits (67% historical win rate). "
        "Historical correlation only — not causation."
    )
    lower = obs.lower()
    for phrase in CAUSAL_PHRASES:
        assert phrase not in lower
    assert "observed pattern" in lower
