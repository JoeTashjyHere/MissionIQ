"""Connector + sync-job + automation state machines and provenance vocabulary.

Mirrors test_document_status.py: the model vocabularies, the progress map, and
the migration must agree, so drift is caught at unit-test time.
"""
from __future__ import annotations

from app.models.connector import (
    AUTOMATION_STATUSES,
    AUTOMATION_TRIGGERS,
    CONNECTOR_STATUSES,
    CONNECTOR_TYPES,
    CREDENTIAL_TYPES,
    SOURCE_TYPES,
    SYNC_JOB_PROGRESS,
    SYNC_JOB_STATUSES,
    SYNC_JOB_TRIGGERS,
)


def test_connector_states_match_milestone_contract():
    assert CONNECTOR_STATUSES == (
        "connected",
        "disconnected",
        "syncing",
        "failed",
        "disabled",
    )


def test_connector_types_match_milestone_contract():
    assert CONNECTOR_TYPES == (
        "crm",
        "document_repository",
        "market_intelligence",
        "project_management",
        "knowledge_management",
    )


def test_sync_job_status_progression_is_complete_and_monotonic():
    assert set(SYNC_JOB_PROGRESS) == set(SYNC_JOB_STATUSES)
    running = ["queued", "connecting", "discovering", "ingesting"]
    values = [SYNC_JOB_PROGRESS[s] for s in running]
    assert values == sorted(values)
    for terminal in ("succeeded", "partial", "failed"):
        assert SYNC_JOB_PROGRESS[terminal] == 100


def test_sync_triggers_reserve_future_entry_points():
    # "scheduled" and "webhook" are schema-reserved so future sync entry
    # points need no migration.
    assert set(SYNC_JOB_TRIGGERS) == {"manual", "scheduled", "webhook", "automation"}


def test_automation_vocabulary():
    assert set(AUTOMATION_TRIGGERS) == {"connector", "manual"}
    assert set(AUTOMATION_STATUSES) == {
        "queued",
        "running",
        "succeeded",
        "partial",
        "failed",
    }


def test_credential_types():
    assert set(CREDENTIAL_TYPES) == {"api_key", "oauth", "basic", "none"}


def test_provenance_source_types():
    assert SOURCE_TYPES == ("user_upload", "connector")


def test_migration_matches_model_vocabularies():
    """The 0005 migration redefines the vocabularies for its CHECK
    constraints; they must not drift from the models."""
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0005_connectors_automation.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0005", path)
    assert spec and spec.loader
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert mig.CONNECTOR_TYPES == CONNECTOR_TYPES
    assert mig.CONNECTOR_STATUSES == CONNECTOR_STATUSES
    assert mig.CREDENTIAL_TYPES == CREDENTIAL_TYPES
    assert mig.SYNC_JOB_TRIGGERS == SYNC_JOB_TRIGGERS
    assert mig.SYNC_JOB_STATUSES == SYNC_JOB_STATUSES
    assert mig.AUTOMATION_TRIGGERS == AUTOMATION_TRIGGERS
    assert mig.AUTOMATION_STATUSES == AUTOMATION_STATUSES
    assert mig.SOURCE_TYPES == SOURCE_TYPES


def test_document_and_opportunity_models_carry_provenance():
    from app.models import Document, Opportunity

    for model in (Document, Opportunity):
        cols = {c.name for c in model.__table__.columns}
        assert {"source_type", "source_connector_id", "source_external_id"} <= cols
        assert model.__table__.columns["source_type"].default.arg == "user_upload"
