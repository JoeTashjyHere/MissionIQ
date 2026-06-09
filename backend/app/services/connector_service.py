"""Connector instance lifecycle + the sync engine.

CRUD mirrors the other workspace-scoped services; the sync engine mirrors the
document pipeline: a queued ``ConnectorSyncJob`` row is advanced through an
explicit status state machine by a FastAPI background task running in its own
``session_scope`` session, with an audit event per stage.

Sync stages:

    queued → connecting → discovering → ingesting → succeeded | partial | failed

Ingestion is idempotent: opportunities upsert on
``(workspace_id, source_connector_id, source_external_id)`` and documents
dedupe by content hash inside ``document_service.upload_document``.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector_registry
from app.connectors.base import (
    BaseConnectorProvider,
    DiscoveryResult,
    ExternalDocument,
    ExternalOpportunity,
)
from app.connectors.credentials import decrypt_secret, encrypt_secret
from app.core.errors import AppError, NotFoundError
from app.ingestion import process_document
from app.models import (
    AutomationRun,
    Connector,
    ConnectorCredential,
    ConnectorSyncJob,
    Opportunity,
)
from app.models.connector import SYNC_JOB_PROGRESS
from app.models.opportunity import CAPTURE_STAGES
from app.schemas.connector import (
    ConnectorCreate,
    ConnectorHealthSummary,
    ConnectorProviderSpec,
    ConnectorResponse,
    ConnectorTestResult,
    ConnectorUpdate,
    SyncJobResponse,
)
from app.services import document_service
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)


# ── Provider catalog ────────────────────────────────────────────────────────


def list_providers() -> list[ConnectorProviderSpec]:
    return [
        ConnectorProviderSpec(
            provider_id=p.provider_id,
            label=p.label,
            description=p.description,
            connector_type=p.connector_type,
            auth_mode=p.auth_mode,
            phase=p.phase,
            implemented=p.implemented,
            provides_opportunities=p.provides_opportunities,
            provides_documents=p.provides_documents,
            requires_customer_authorization=p.requires_customer_authorization,
            config_fields=p.config_fields,
        )
        for p in get_connector_registry().all()
    ]


def _provider_for(connector: Connector) -> BaseConnectorProvider:
    cls = get_connector_registry().require(connector.provider_id)
    return cls()


# ── Response building ───────────────────────────────────────────────────────


async def _credential_for(
    db: AsyncSession, connector_id: uuid.UUID
) -> ConnectorCredential | None:
    stmt = select(ConnectorCredential).where(
        ConnectorCredential.connector_id == connector_id
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def to_response(db: AsyncSession, connector: Connector) -> ConnectorResponse:
    resp = ConnectorResponse.model_validate(connector)
    cred = await _credential_for(db, connector.id)
    if cred is not None:
        resp.credential_set = bool(cred.secret_encrypted)
        resp.credential_type = cred.credential_type
        resp.last_validated_at = cred.last_validated_at
    return resp


# ── CRUD ────────────────────────────────────────────────────────────────────


async def list_connectors(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[ConnectorResponse]:
    stmt = (
        select(Connector)
        .where(Connector.workspace_id == workspace_id)
        .order_by(Connector.created_at)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [await to_response(db, c) for c in rows]


async def get_connector(
    db: AsyncSession, workspace_id: uuid.UUID, connector_id: uuid.UUID
) -> Connector:
    connector = await db.get(Connector, connector_id)
    if connector is None or connector.workspace_id != workspace_id:
        raise NotFoundError("Connector not found.", code="connector.not_found")
    return connector


async def create_connector(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ConnectorCreate,
) -> Connector:
    provider = get_connector_registry().require(payload.provider_id)
    if not provider.implemented:
        raise AppError(
            f"The {provider.label} connector is a planned integration and "
            "cannot be configured yet.",
            status_code=422,
            code="connector.not_implemented",
        )
    connector = Connector(
        workspace_id=workspace_id,
        provider_id=provider.provider_id,
        connector_type=provider.connector_type,
        name=payload.name,
        status="disconnected",
        config=payload.config,
        auto_create_pursuits=payload.auto_create_pursuits,
        auto_run_automation=payload.auto_run_automation,
        created_by_user_id=user_id,
    )
    db.add(connector)
    await db.flush()
    db.add(
        ConnectorCredential(
            connector_id=connector.id,
            workspace_id=workspace_id,
            credential_type=provider.auth_mode,
            secret_encrypted=(
                encrypt_secret(payload.credential) if payload.credential else None
            ),
        )
    )
    await db.flush()
    return connector


async def update_connector(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    connector_id: uuid.UUID,
    payload: ConnectorUpdate,
) -> Connector:
    connector = await get_connector(db, workspace_id, connector_id)
    if payload.name is not None:
        connector.name = payload.name
    if payload.config is not None:
        connector.config = payload.config
    if payload.auto_create_pursuits is not None:
        connector.auto_create_pursuits = payload.auto_create_pursuits
    if payload.auto_run_automation is not None:
        connector.auto_run_automation = payload.auto_run_automation
    if payload.enabled is not None:
        connector.status = "disconnected" if payload.enabled else "disabled"
    if payload.credential is not None:
        cred = await _credential_for(db, connector.id)
        if cred is None:
            cred = ConnectorCredential(
                connector_id=connector.id, workspace_id=workspace_id
            )
            db.add(cred)
        cred.secret_encrypted = encrypt_secret(payload.credential)
        cred.last_validated_at = None
    await db.flush()
    return connector


async def delete_connector(
    db: AsyncSession, *, workspace_id: uuid.UUID, connector_id: uuid.UUID
) -> None:
    connector = await get_connector(db, workspace_id, connector_id)
    await db.delete(connector)
    await db.flush()


# ── Connection test ─────────────────────────────────────────────────────────


async def _secret_for(db: AsyncSession, connector: Connector) -> str | None:
    cred = await _credential_for(db, connector.id)
    if cred is None or not cred.secret_encrypted:
        return None
    return decrypt_secret(cred.secret_encrypted)


async def test_connection(
    db: AsyncSession, *, workspace_id: uuid.UUID, connector_id: uuid.UUID
) -> ConnectorTestResult:
    connector = await get_connector(db, workspace_id, connector_id)
    provider = _provider_for(connector)
    secret = await _secret_for(db, connector)
    health = await provider.test_connection(config=connector.config, secret=secret)
    now = datetime.now(UTC)
    if health.ok:
        if connector.status in ("disconnected", "failed"):
            connector.status = "connected"
        cred = await _credential_for(db, connector.id)
        if cred is not None:
            cred.last_validated_at = now
    elif connector.status == "connected":
        connector.status = "failed"
    await db.flush()
    return ConnectorTestResult(ok=health.ok, message=health.message, checked_at=now)


# ── Sync jobs ───────────────────────────────────────────────────────────────


async def enqueue_sync_job(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    connector_id: uuid.UUID,
    user_id: uuid.UUID | None,
    trigger: str = "manual",
) -> ConnectorSyncJob:
    connector = await get_connector(db, workspace_id, connector_id)
    if connector.status == "disabled":
        raise AppError(
            "Connector is disabled. Re-enable it before syncing.",
            status_code=409,
            code="connector.disabled",
        )
    job = ConnectorSyncJob(
        connector_id=connector.id,
        workspace_id=workspace_id,
        trigger=trigger,
        status="queued",
        progress_pct=SYNC_JOB_PROGRESS["queued"],
        stats={},
        triggered_by_user_id=user_id,
    )
    db.add(job)
    await db.flush()
    return job


def _job_response(job: ConnectorSyncJob, connector: Connector | None) -> SyncJobResponse:
    resp = SyncJobResponse.model_validate(job)
    if connector is not None:
        resp.connector_name = connector.name
        resp.provider_id = connector.provider_id
    return resp


async def list_jobs(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    connector_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[SyncJobResponse]:
    stmt = (
        select(ConnectorSyncJob, Connector)
        .join(Connector, ConnectorSyncJob.connector_id == Connector.id)
        .where(ConnectorSyncJob.workspace_id == workspace_id)
        .order_by(ConnectorSyncJob.created_at.desc())
        .limit(limit)
    )
    if connector_id is not None:
        stmt = stmt.where(ConnectorSyncJob.connector_id == connector_id)
    rows = (await db.execute(stmt)).all()
    return [_job_response(job, connector) for job, connector in rows]


async def health_summary(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> ConnectorHealthSummary:
    connectors = await list_connectors(db, workspace_id)
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    jobs_24h = (
        await db.execute(
            select(func.count())
            .select_from(ConnectorSyncJob)
            .where(ConnectorSyncJob.workspace_id == workspace_id)
            .where(ConnectorSyncJob.created_at >= cutoff)
        )
    ).scalar_one()
    failed_24h = (
        await db.execute(
            select(func.count())
            .select_from(ConnectorSyncJob)
            .where(ConnectorSyncJob.workspace_id == workspace_id)
            .where(ConnectorSyncJob.created_at >= cutoff)
            .where(ConnectorSyncJob.status == "failed")
        )
    ).scalar_one()
    automation_24h = (
        await db.execute(
            select(func.count())
            .select_from(AutomationRun)
            .where(AutomationRun.workspace_id == workspace_id)
            .where(AutomationRun.created_at >= cutoff)
        )
    ).scalar_one()

    by_status = {s: 0 for s in ("connected", "syncing", "failed", "disabled", "disconnected")}
    for c in connectors:
        by_status[c.status] = by_status.get(c.status, 0) + 1
    return ConnectorHealthSummary(
        total=len(connectors),
        connected=by_status["connected"],
        syncing=by_status["syncing"],
        failed=by_status["failed"],
        disabled=by_status["disabled"],
        disconnected=by_status["disconnected"],
        jobs_24h=jobs_24h,
        failed_jobs_24h=failed_24h,
        automation_runs_24h=automation_24h,
        connectors=connectors,
    )


# ── Sync engine ─────────────────────────────────────────────────────────────


async def _advance_job(
    db: AsyncSession, job: ConnectorSyncJob, status: str, **fields: object
) -> None:
    job.status = status
    job.progress_pct = SYNC_JOB_PROGRESS.get(status, job.progress_pct)
    for key, value in fields.items():
        setattr(job, key, value)
    await write_audit(
        db,
        action=f"connector.sync.{status}",
        workspace_id=job.workspace_id,
        target_type="connector_sync_job",
        target_id=str(job.id),
        meta={"connector_id": str(job.connector_id), "stats": job.stats},
    )
    await db.flush()


async def _upsert_opportunity(
    db: AsyncSession,
    *,
    connector: Connector,
    ext: ExternalOpportunity,
    stats: dict[str, int],
) -> Opportunity | None:
    stmt = select(Opportunity).where(
        Opportunity.workspace_id == connector.workspace_id,
        Opportunity.source_connector_id == connector.id,
        Opportunity.source_external_id == ext.external_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        # Refresh connector-owned metadata without clobbering analyst edits to
        # notes or stage.
        for attr in (
            "agency",
            "sub_agency",
            "contract_vehicle",
            "solicitation_number",
            "naics_code",
            "set_aside",
            "due_date",
            "estimated_value_cents",
            "incumbent",
        ):
            value = getattr(ext, attr)
            if value is not None:
                setattr(existing, attr, value)
        stats["opportunities_updated"] = stats.get("opportunities_updated", 0) + 1
        return existing

    if not connector.auto_create_pursuits:
        stats["items_skipped"] = stats.get("items_skipped", 0) + 1
        return None

    stage = ext.capture_stage if ext.capture_stage in CAPTURE_STAGES else "identification"
    opp = Opportunity(
        workspace_id=connector.workspace_id,
        name=ext.name,
        agency=ext.agency,
        sub_agency=ext.sub_agency,
        contract_vehicle=ext.contract_vehicle,
        solicitation_number=ext.solicitation_number,
        naics_code=ext.naics_code,
        set_aside=ext.set_aside,
        due_date=ext.due_date,
        estimated_value_cents=ext.estimated_value_cents,
        incumbent=ext.incumbent,
        capture_stage=stage,
        notes=ext.notes,
        created_by_user_id=connector.created_by_user_id,
        source_type="connector",
        source_connector_id=connector.id,
        source_external_id=ext.external_id,
    )
    db.add(opp)
    await db.flush()
    stats["opportunities_created"] = stats.get("opportunities_created", 0) + 1
    await write_audit(
        db,
        action="opportunity.created",
        workspace_id=connector.workspace_id,
        target_type="opportunity",
        target_id=str(opp.id),
        meta={"source": "connector", "connector_id": str(connector.id)},
    )
    return opp


async def _resolve_doc_opportunity(
    db: AsyncSession,
    *,
    connector: Connector,
    ext_doc: ExternalDocument,
    created: dict[str, uuid.UUID],
) -> uuid.UUID | None:
    if ext_doc.opportunity_external_id:
        if ext_doc.opportunity_external_id in created:
            return created[ext_doc.opportunity_external_id]
        stmt = select(Opportunity.id).where(
            Opportunity.workspace_id == connector.workspace_id,
            Opportunity.source_connector_id == connector.id,
            Opportunity.source_external_id == ext_doc.opportunity_external_id,
        )
        found = (await db.execute(stmt)).scalar_one_or_none()
        if found is not None:
            return found
    if ext_doc.opportunity_name_hint:
        stmt = select(Opportunity.id).where(
            Opportunity.workspace_id == connector.workspace_id,
            func.lower(Opportunity.name) == ext_doc.opportunity_name_hint.lower(),
        )
        return (await db.execute(stmt)).scalar_one_or_none()
    return None


async def _ingest_document(
    db: AsyncSession,
    *,
    connector: Connector,
    provider: BaseConnectorProvider,
    secret: str | None,
    ext_doc: ExternalDocument,
    opportunity_id: uuid.UUID,
    stats: dict[str, int],
) -> None:
    data = await provider.fetch_document(
        config=connector.config, secret=secret, ref=ext_doc
    )
    doc = await document_service.upload_document(
        db,
        workspace_id=connector.workspace_id,
        opportunity_id=opportunity_id,
        user_id=None,
        filename=ext_doc.filename,
        mime_type=ext_doc.mime_type,
        data=data,
        doc_type=ext_doc.doc_type,
        source_type="connector",
        source_connector_id=connector.id,
        source_external_id=ext_doc.external_id,
    )
    if doc.status != "ready":
        # New (or re-queued) document: run the existing ingestion pipeline so
        # connector-ingested material is indexed exactly like uploads.
        await process_document(db=db, document_id=doc.id)
    stats["documents_ingested"] = stats.get("documents_ingested", 0) + 1


async def run_sync_job(db: AsyncSession, *, job_id: uuid.UUID) -> None:
    """Execute one sync job to completion. Runs in a background task with its
    own session (the document-pipeline pattern)."""
    job = await db.get(ConnectorSyncJob, job_id)
    if job is None:
        logger.warning("sync job %s vanished before execution", job_id)
        return
    connector = await db.get(Connector, job.connector_id)
    if connector is None:
        return

    stats: dict[str, int] = {}
    created_pursuits: dict[str, uuid.UUID] = {}
    failures: list[str] = []
    connector.status = "syncing"
    connector.last_sync_at = datetime.now(UTC)
    job.started_at = datetime.now(UTC)

    try:
        provider = _provider_for(connector)
        secret = await _secret_for(db, connector)

        await _advance_job(db, job, "connecting")
        health = await provider.test_connection(config=connector.config, secret=secret)
        if not health.ok:
            raise AppError(health.message, status_code=502, code="connector.unreachable")

        await _advance_job(db, job, "discovering")
        result: DiscoveryResult = await provider.discover(
            config=connector.config, secret=secret, since=connector.last_success_at
        )
        stats["items_discovered"] = len(result.opportunities) + len(result.documents)

        await _advance_job(db, job, "ingesting", stats=dict(stats))

        for ext in result.opportunities:
            existing_count = stats.get("opportunities_created", 0)
            opp = await _upsert_opportunity(db, connector=connector, ext=ext, stats=stats)
            if opp is None:
                continue
            if stats.get("opportunities_created", 0) > existing_count:
                created_pursuits[ext.external_id] = opp.id
            for attachment in ext.attachments:
                try:
                    await _ingest_document(
                        db,
                        connector=connector,
                        provider=provider,
                        secret=secret,
                        ext_doc=attachment,
                        opportunity_id=opp.id,
                        stats=stats,
                    )
                except Exception as exc:  # noqa: BLE001 — per-item isolation
                    stats["items_failed"] = stats.get("items_failed", 0) + 1
                    failures.append(f"{attachment.filename}: {exc}")
                    logger.exception("connector doc ingest failed: %s", attachment.filename)

        for ext_doc in result.documents:
            opp_id = await _resolve_doc_opportunity(
                db, connector=connector, ext_doc=ext_doc, created=created_pursuits
            )
            if opp_id is None:
                stats["items_skipped"] = stats.get("items_skipped", 0) + 1
                continue
            try:
                await _ingest_document(
                    db,
                    connector=connector,
                    provider=provider,
                    secret=secret,
                    ext_doc=ext_doc,
                    opportunity_id=opp_id,
                    stats=stats,
                )
            except Exception as exc:  # noqa: BLE001 — per-item isolation
                stats["items_failed"] = stats.get("items_failed", 0) + 1
                failures.append(f"{ext_doc.filename}: {exc}")
                logger.exception("connector doc ingest failed: %s", ext_doc.filename)

        final = "partial" if stats.get("items_failed") else "succeeded"
        connector.status = "connected"
        connector.last_success_at = datetime.now(UTC)
        connector.consecutive_failures = 0
        await _advance_job(
            db,
            job,
            final,
            stats=stats,
            finished_at=datetime.now(UTC),
            error_message="; ".join(failures)[:1000] or None,
        )
    except Exception as exc:  # noqa: BLE001 — job must record its own failure
        logger.exception("sync job %s failed", job_id)
        connector.status = "failed"
        connector.consecutive_failures += 1
        await _advance_job(
            db,
            job,
            "failed",
            stats=stats,
            finished_at=datetime.now(UTC),
            error_message=str(exc)[:1000],
        )
        return

    # Pursuit automation for newly created pursuits (same background context).
    if connector.auto_run_automation and created_pursuits:
        from app.services import automation_service  # lazy: avoids import cycle

        for opp_id in created_pursuits.values():
            try:
                run = await automation_service.enqueue_run(
                    db,
                    workspace_id=connector.workspace_id,
                    opportunity_id=opp_id,
                    user_id=connector.created_by_user_id,
                    trigger="connector",
                    connector_sync_job_id=job.id,
                )
                await automation_service.execute_run(db, run_id=run.id)
            except Exception:  # noqa: BLE001 — automation never fails the sync
                logger.exception("automation run failed for opportunity %s", opp_id)
