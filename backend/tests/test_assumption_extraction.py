"""Assumption extraction tests.

The Assumption Validation panel is fed by a pure walk over module output
JSON: every object the AI tagged ``basis: "assumption"`` becomes a
validatable item with a stable key. The original assumption lives untouched
in ``ai_output.output_json`` — extraction never mutates anything.
"""
from __future__ import annotations

from app.services.governance_service import assumption_key, extract_assumptions


def test_extracts_strategic_points_tagged_assumption():
    output = {
        "win_themes": [
            {"statement": "Incumbent staff will transition.", "basis": "assumption"},
            {"statement": "Agency values automation.", "basis": "evidence"},
        ],
    }
    found = extract_assumptions(output)
    assert len(found) == 1
    key, text, path = found[0]
    assert text == "Incumbent staff will transition."
    assert path == "win_themes"
    assert key == assumption_key("win_themes", text)


def test_extracts_nested_and_varied_shapes():
    output = {
        "win_confidence_assessment": {
            "score": 62,
            "rationale": "Limited past performance data.",
            "basis": "assumption",
        },
        "black_hat": [
            {
                "competitor_move": "Incumbent will undercut on price.",
                "impact": "high",
                "our_counter": "Emphasize transition risk.",
                "basis": "assumption",
            }
        ],
        "risks": [
            {"title": "Clearance timeline", "severity": "high", "basis": "assumption"},
        ],
        "decision_factors": [
            {
                "name": "Customer intimacy",
                "score": 40,
                "rationale": "No documented agency relationships.",
                "basis": "assumption",
            },
        ],
    }
    found = extract_assumptions(output)
    texts = {text for _, text, _ in found}
    assert "Limited past performance data." in texts
    assert "Incumbent will undercut on price." in texts
    assert "Clearance timeline" in texts
    # Named factors combine name + rationale for a self-contained record.
    assert "Customer intimacy: No documented agency relationships." in texts
    assert len(found) == 4


def test_ignores_evidence_and_inference():
    output = {
        "points": [
            {"statement": "A", "basis": "evidence"},
            {"statement": "B", "basis": "inference"},
        ]
    }
    assert extract_assumptions(output) == []


def test_modules_without_basis_tags_yield_nothing():
    # e.g. Customer DNA shapes — honest empty state, no invented assumptions.
    output = {"mission": {"summary": "text"}, "priorities": ["a", "b"]}
    assert extract_assumptions(output) == []


def test_keys_are_stable_across_list_reordering():
    a = {"points": [{"statement": "X", "basis": "assumption"}, {"statement": "Y", "basis": "assumption"}]}
    b = {"points": [{"statement": "Y", "basis": "assumption"}, {"statement": "X", "basis": "assumption"}]}
    keys_a = {key for key, _, _ in extract_assumptions(a)}
    keys_b = {key for key, _, _ in extract_assumptions(b)}
    assert keys_a == keys_b  # list indices are excluded from paths


def test_key_is_path_scoped():
    # The same statement under different fields is a different assumption.
    output = {
        "win_themes": [{"statement": "Same words.", "basis": "assumption"}],
        "risks": [{"statement": "Same words.", "basis": "assumption"}],
    }
    keys = {key for key, _, _ in extract_assumptions(output)}
    assert len(keys) == 2


def test_key_normalizes_whitespace_and_case():
    assert assumption_key("p", "Incumbent  Will\nTransition") == assumption_key(
        "p", "incumbent will transition"
    )


def test_duplicate_statements_dedupe():
    output = {
        "points": [
            {"statement": "Dup", "basis": "assumption"},
            {"statement": "Dup", "basis": "assumption"},
        ]
    }
    assert len(extract_assumptions(output)) == 1


def test_extraction_does_not_mutate_output():
    output = {"points": [{"statement": "X", "basis": "assumption"}]}
    snapshot = {"points": [{"statement": "X", "basis": "assumption"}]}
    extract_assumptions(output)
    assert output == snapshot
