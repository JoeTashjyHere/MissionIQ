"""Pursuit Automation Orchestrator.

Executes a declarative step plan against a pursuit and records every step in
``automation_run.steps`` (auditable JSONB). The orchestration core
(``run_steps``) is a pure async function over injected executors so retry,
critical-abort, and partial-failure semantics are unit-testable without a
database; ``execute_run`` wires in the DB-bound executors.

Step plan (order preserves the Customer DNA dependency chain):

    pursuit_ready → documents_ready → market_intel → customer_dna →
    company_dna → capability_match → win_strategy → executive_brief

Semantics:
- Each step retries up to ``max_attempts`` (immediate retry).
- A *critical* step failure marks all remaining steps ``skipped`` and the run
  ``failed`` (pursuit_ready, customer_dna — everything downstream consumes it).
- Non-critical failures continue; the run finishes ``partial``.
- A module returning ``insufficient_context`` is an *honest* outcome, not a
  failure: the step succeeds and records the module status. Epistemic honesty
  is preserved — automation never fabricates inputs to force an output.
- Retrying a run re-executes from the first non-succeeded step.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.integrations.sam_gov import SamGovClient
from app.models import AutomationRun, Document, Opportunity, User, Workspace
from app.schemas.automation import AutomationRunResponse, AutomationStepResult
from app.services import intelligence_service, market_intel_service
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

DOC_WAIT_TIMEOUT_SECONDS = 90
DOC_WAIT_POLL_SECONDS = 3.0
MARKET_INTEL_TOP_N = 3

_PROCESSING_DOC_STATUSES = ("uploaded", "parsing", "chunking", "embedding")


@dataclass(frozen=True)
class AutomationStepDef:
    step_id: str
    label: str
    critical: bool = False
    max_attempts: int = 2


def build_step_plan() -> list[AutomationStepDef]:
    """The declarative pursuit-automation plan. Extending the workflow is a
    list entry + an executor."""
    return [
        AutomationStepDef("pursuit_ready", "Pursuit workspace ready", critical=True),
        AutomationStepDef("documents_ready", "Document ingestion settled"),
        AutomationStepDef("market_intel", "Market intelligence associated"),
        AutomationStepDef("customer_dna", "Customer DNA generated", critical=True),
        AutomationStepDef("company_dna", "Company DNA generated"),
        AutomationStepDef("capability_match", "Capability Match generated"),
        AutomationStepDef("win_strategy", "Win Strategy generated"),
        AutomationStepDef("executive_brief", "Executive Brief generated"),
    ]


def initial_step_results(plan: list[AutomationStepDef] | None = None) -> list[dict]:
    plan = plan or build_step_plan()
    return [
        AutomationStepResult(step_id=s.step_id, label=s.label).model_dump()
        for s in plan
    ]


StepExecutor = Callable[[], Awaitable[dict | None]]
UpdateHook = Callable[[str | None], Awaitable[None]]


async def run_steps(
    plan: list[AutomationStepDef],
    executors: dict[str, StepExecutor],
    results: list[dict],
    on_update: UpdateHook | None = None,
) -> str:
    """Execute the plan, mutating ``results`` in place. Returns the final run
    status: ``succeeded`` | ``partial`` | ``failed``."""
    by_id = {r["step_id"]: r for r in results}
    aborted = False
    any_failure = False

    async def _notify(current: str | None) -> None:
        if on_update is not None:
            await on_update(current)

    for step in plan:
        result = by_id.get(step.step_id)
        if result is None:
            result = AutomationStepResult(
                step_id=step.step_id, label=step.label
            ).model_dump()
            results.append(result)
            by_id[step.step_id] = result
        if result["status"] == "succeeded":
            continue
        if aborted:
            result["status"] = "skipped"
            result["error"] = "Skipped: a critical upstream step failed."
            continue

        executor = executors.get(step.step_id)
        if executor is None:
            result["status"] = "skipped"
            result["error"] = "No executor registered for this step."
            any_failure = True
            continue

        result["status"] = "running"
        result["started_at"] = datetime.now(UTC).isoformat()
        await _notify(step.step_id)

        last_error: str | None = None
        for attempt in range(1, step.max_attempts + 1):
            result["attempts"] = result.get("attempts", 0) + 1
            try:
                detail = await executor()
                result["status"] = "succeeded"
                result["error"] = None
                if detail:
                    result.update(detail)
                break
            except Exception as exc:  # noqa: BLE001 — recorded, retried, surfaced
                last_error = str(exc)[:500]
                logger.warning(
                    "automation step %s attempt %d failed: %s",
                    step.step_id,
                    attempt,
                    last_error,
                )
        else:
            result["status"] = "failed"
            result["error"] = last_error
            any_failure = True
            if step.critical:
                aborted = True
        result["finished_at"] = datetime.now(UTC).isoformat()
        await _notify(step.step_id)

    if aborted:
        return "failed"
    return "partial" if any_failure else "succeeded"


# ── Run lifecycle ───────────────────────────────────────────────────────────


async def enqueue_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    user_id: uuid.UUID | None,
    trigger: str = "manual",
    connector_sync_job_id: uuid.UUID | None = None,
) -> AutomationRun:
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")
    run = AutomationRun(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        trigger=trigger,
        status="queued",
        steps=initial_step_results(),
        triggered_by_user_id=user_id,
        connector_sync_job_id=connector_sync_job_id,
    )
    db.add(run)
    await db.flush()
    await write_audit(
        db,
        action="automation.run.queued",
        workspace_id=workspace_id,
        target_type="automation_run",
        target_id=str(run.id),
        meta={"opportunity_id": str(opportunity_id), "trigger": trigger},
    )
    return run


async def _actor_for(db: AsyncSession, run: AutomationRun) -> User:
    """Module runs attribute generated intelligence to a user. Prefer the
    triggering user, fall back to the workspace owner."""
    if run.triggered_by_user_id is not None:
        user = await db.get(User, run.triggered_by_user_id)
        if user is not None:
            return user
    ws = await db.get(Workspace, run.workspace_id)
    if ws is not None and ws.owner_user_id is not None:
        owner = await db.get(User, ws.owner_user_id)
        if owner is not None:
            return owner
    raise AppError(
        "No actor available for automation run.",
        status_code=409,
        code="automation.no_actor",
    )


def _build_executors(
    db: AsyncSession, *, run: AutomationRun, opp: Opportunity, actor: User
) -> dict[str, StepExecutor]:
    async def pursuit_ready() -> dict:
        return {"detail": f"Pursuit workspace ready: {opp.name}"}

    async def documents_ready() -> dict:
        deadline = datetime.now(UTC) + timedelta(seconds=DOC_WAIT_TIMEOUT_SECONDS)
        while True:
            stmt = select(Document.status).where(
                Document.workspace_id == run.workspace_id,
                Document.opportunity_id == run.opportunity_id,
                Document.deleted_at.is_(None),
            )
            statuses = list((await db.execute(stmt)).scalars().all())
            if not statuses:
                return {
                    "detail": (
                        "No documents in the pursuit. Downstream modules will "
                        "flag missing inputs honestly."
                    )
                }
            processing = [s for s in statuses if s in _PROCESSING_DOC_STATUSES]
            if not processing:
                ready = sum(1 for s in statuses if s == "ready")
                failed = sum(1 for s in statuses if s == "failed")
                return {"detail": f"{ready} document(s) ready, {failed} failed."}
            if datetime.now(UTC) >= deadline:
                return {
                    "detail": (
                        f"Timed out with {len(processing)} document(s) still "
                        "processing; continuing."
                    )
                }
            await asyncio.sleep(DOC_WAIT_POLL_SECONDS)

    async def market_intel() -> dict:
        client = SamGovClient()
        if not client.is_configured():
            return {"detail": "SAM.gov not configured — step skipped gracefully."}
        items = await market_intel_service.search_sam(
            q=opp.name,
            agency=opp.agency,
            naics=opp.naics_code,
            posted_after=None,
            due_before=None,
            limit=MARKET_INTEL_TOP_N,
        )
        if not items:
            return {"detail": "No matching public market intelligence found."}
        records = await market_intel_service.upsert_records_for_workspace(
            db, workspace_id=run.workspace_id, source_id="sam_gov", payloads=items
        )
        for record in records:
            await market_intel_service.link_record_to_opportunity(
                db,
                workspace_id=run.workspace_id,
                opportunity_id=run.opportunity_id,
                market_intel_record_id=record.id,
                user_id=actor.id,
                notes="Linked by pursuit automation.",
            )
        return {"detail": f"Linked {len(records)} market intelligence record(s)."}

    def module_step(module_id: str) -> StepExecutor:
        async def _exec() -> dict:
            resp = await intelligence_service.run_module(
                db,
                workspace_id=run.workspace_id,
                opportunity_id=run.opportunity_id,
                module_id=module_id,
                user=actor,
            )
            return {
                "ai_output_id": str(resp.id),
                "detail": f"{module_id} → {resp.status}",
            }

        return _exec

    return {
        "pursuit_ready": pursuit_ready,
        "documents_ready": documents_ready,
        "market_intel": market_intel,
        "customer_dna": module_step("capture.customer_dna"),
        "company_dna": module_step("capture.company_dna"),
        "capability_match": module_step("capture.capability_match"),
        "win_strategy": module_step("capture.win_strategy"),
        "executive_brief": module_step("capture.executive_brief"),
    }


async def execute_run(db: AsyncSession, *, run_id: uuid.UUID) -> AutomationRun:
    """Execute (or resume) an automation run to completion. Runs in a
    background task with its own session, like the document pipeline."""
    run = await db.get(AutomationRun, run_id)
    if run is None:
        raise NotFoundError("Automation run not found.", code="automation.not_found")
    opp = await db.get(Opportunity, run.opportunity_id)
    if opp is None:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")
    actor = await _actor_for(db, run)

    run.status = "running"
    run.started_at = run.started_at or datetime.now(UTC)
    run.error_message = None
    await db.flush()
    await write_audit(
        db,
        action="automation.run.started",
        workspace_id=run.workspace_id,
        target_type="automation_run",
        target_id=str(run.id),
        meta={"opportunity_id": str(run.opportunity_id)},
    )

    results = [dict(r) for r in (run.steps or [])]

    async def persist(current_step: str | None) -> None:
        run.current_step = current_step
        run.steps = [dict(r) for r in results]  # reassign → JSONB change tracked
        await db.flush()

    plan = build_step_plan()
    executors = _build_executors(db, run=run, opp=opp, actor=actor)
    try:
        final = await run_steps(plan, executors, results, on_update=persist)
    except Exception as exc:  # noqa: BLE001 — the run must record its failure
        logger.exception("automation run %s crashed", run_id)
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.now(UTC)
        run.steps = [dict(r) for r in results]
        await db.flush()
        return run

    run.status = final
    run.current_step = None
    run.finished_at = datetime.now(UTC)
    run.steps = [dict(r) for r in results]
    failed = [r["step_id"] for r in results if r["status"] == "failed"]
    run.error_message = (
        f"Failed steps: {', '.join(failed)}" if failed else None
    )
    await db.flush()
    await write_audit(
        db,
        action=f"automation.run.{final}",
        workspace_id=run.workspace_id,
        target_type="automation_run",
        target_id=str(run.id),
        meta={"opportunity_id": str(run.opportunity_id), "failed_steps": failed},
    )
    return run


async def retry_run(
    db: AsyncSession, *, workspace_id: uuid.UUID, run_id: uuid.UUID
) -> AutomationRun:
    """Reset failed/skipped steps to pending so execute_run resumes from the
    first non-succeeded step."""
    run = await db.get(AutomationRun, run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Automation run not found.", code="automation.not_found")
    if run.status in ("queued", "running"):
        raise AppError(
            "Automation run is still in progress.",
            status_code=409,
            code="automation.in_progress",
        )
    steps = [dict(r) for r in (run.steps or [])]
    for r in steps:
        if r["status"] in ("failed", "skipped", "running"):
            r["status"] = "pending"
            r["error"] = None
    run.steps = steps
    run.status = "queued"
    run.finished_at = None
    run.error_message = None
    await db.flush()
    return run


# ── Queries ─────────────────────────────────────────────────────────────────


async def _run_response(db: AsyncSession, run: AutomationRun) -> AutomationRunResponse:
    resp = AutomationRunResponse.model_validate(run)
    opp = await db.get(Opportunity, run.opportunity_id)
    if opp is not None:
        resp.opportunity_name = opp.name
    return resp


async def list_runs_for_opportunity(
    db: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> list[AutomationRunResponse]:
    stmt = (
        select(AutomationRun)
        .where(
            AutomationRun.workspace_id == workspace_id,
            AutomationRun.opportunity_id == opportunity_id,
        )
        .order_by(AutomationRun.created_at.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [await _run_response(db, r) for r in rows]


async def list_runs_for_workspace(
    db: AsyncSession, *, workspace_id: uuid.UUID, limit: int = 50
) -> list[AutomationRunResponse]:
    stmt = (
        select(AutomationRun)
        .where(AutomationRun.workspace_id == workspace_id)
        .order_by(AutomationRun.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [await _run_response(db, r) for r in rows]
