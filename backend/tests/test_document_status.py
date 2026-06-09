"""Document processing state machine.

Validates the canonical status vocabulary, the public progress map used by the
UI, and the migration's check constraint matches the model's allowed values.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.models.document import DOC_STATUS_PROGRESS, DOC_STATUSES


EXPECTED_STATUSES = (
    "uploaded",
    "parsing",
    "chunking",
    "embedding",
    "ready",
    "failed",
)


def test_status_vocabulary_matches_product_contract():
    assert DOC_STATUSES == EXPECTED_STATUSES


def test_progress_map_covers_all_statuses():
    assert set(DOC_STATUS_PROGRESS.keys()) == set(EXPECTED_STATUSES)
    for s, pct in DOC_STATUS_PROGRESS.items():
        assert 0 <= pct <= 100, f"{s} progress out of range: {pct}"


def test_progress_is_monotonic_through_happy_path():
    happy_path = ["uploaded", "parsing", "chunking", "embedding", "ready"]
    values = [DOC_STATUS_PROGRESS[s] for s in happy_path]
    assert values == sorted(values), f"Progress regressed: {values}"
    assert DOC_STATUS_PROGRESS["ready"] == 100
    assert DOC_STATUS_PROGRESS["failed"] == 100


def test_migration_check_constraint_lists_same_statuses():
    """The Alembic migration must whitelist exactly the same statuses the model
    advertises, or upgrades will succeed but writes will fail at runtime."""
    migration = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0001_initial.py"
    text = migration.read_text(encoding="utf-8")
    match = re.search(
        r"status IN \(([^)]+)\).*?name=\"ck_document_status\"",
        text,
        re.DOTALL,
    )
    assert match is not None, "ck_document_status constraint not found in migration"
    raw = match.group(1)
    in_migration = tuple(s.strip().strip("'\"") for s in raw.split(","))
    assert in_migration == EXPECTED_STATUSES, (
        f"Migration status list {in_migration} drifted from model {EXPECTED_STATUSES}"
    )
