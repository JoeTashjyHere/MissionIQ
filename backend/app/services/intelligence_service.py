"""Orchestrates module runs: dispatch → persist → structured writeback →
knowledge-graph ingestion → audit."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.graph import service as graph_service
from app.intelligence import get_registry

logger = logging.getLogger(__name__)
from app.intelligence.base import RAGContext
from app.intelligence.citations import build_citations
from app.intelligence.rag import RAGEngine
from app.llm.prompt_library import get_prompt_library
from app.llm.router import get_llm_router
from app.models import (
    AIOutput,
    ComplianceRequirement,
    EvaluationCriterion,
    Opportunity,
    Risk,
    User,
)
from app.schemas.intelligence import AIOutputResponse, ModuleSpec


def list_modules() -> list[ModuleSpec]:
    return [
        ModuleSpec(
            id=m.id,
            group=m.group,
            label=m.label,
            description=m.description,
            version=m.version,
            output_schema_summary=m.output_schema_summary,
            requires_customer_dna=m.requires_customer_dna,
            consumes_company_profile=m.consumes_company_profile,
        )
        for m in get_registry().all()
    ]


def get_module_spec(module_id: str) -> ModuleSpec:
    registry = get_registry()
    cls = registry.get(module_id)
    if cls is None:
        raise NotFoundError(f"Module not registered: {module_id}", code="module.not_found")
    return ModuleSpec(
        id=cls.id,
        group=cls.group,
        label=cls.label,
        description=cls.description,
        version=cls.version,
        output_schema_summary=cls.output_schema_summary,
        requires_customer_dna=cls.requires_customer_dna,
        consumes_company_profile=cls.consumes_company_profile,
    )


async def run_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    user: User,
    model_override: str | None = None,
) -> AIOutputResponse:
    registry = get_registry()
    cls = registry.get(module_id)
    if cls is None:
        raise NotFoundError(f"Module not registered: {module_id}", code="module.not_found")
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.workspace_id != workspace_id:
        raise NotFoundError("Opportunity not found.", code="opportunity.not_found")

    rag = RAGEngine(db=db, llm_router=get_llm_router())
    module = cls(
        db=db,
        rag=rag,
        llm_router=get_llm_router(),
        prompts=get_prompt_library(),
    )
    ctx = RAGContext(workspace_id=workspace_id, opportunity_id=opportunity_id)
    result = await module.run(opportunity=opp, ctx=ctx, model_override=model_override)

    output_row = AIOutput(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=cls.id,
        module_version=cls.version,
        prompt_id=cls.prompt_id,
        prompt_version=cls.prompt_version,
        model_provider=result.llm.provider,
        model_name=result.llm.model,
        input_tokens=result.llm.input_tokens,
        output_tokens=result.llm.output_tokens,
        latency_ms=result.llm.latency_ms,
        output_json=result.output,
        evidence_chunk_ids=[ev.chunk_id for ev in result.evidence if ev.chunk_id],
        evidence_market_record_ids=[
            ev.market_record_id for ev in result.market_evidence if ev.market_record_id
        ],
        status=result.status,
        generated_by_user_id=user.id,
    )
    db.add(output_row)
    await db.flush()

    # Structured writeback for modules whose output maps to first-class
    # relational rows (Compliance / Evaluation / Risk). Replaces prior rows
    # for the same opportunity to keep CSV exports and joined queries in
    # sync with the latest analysis.
    if result.status == "ok":
        if cls.id == "capture.compliance_matrix":
            await _writeback_compliance(
                db,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=output_row.id,
                output=result.output,
            )
        elif cls.id == "capture.evaluation_criteria":
            await _writeback_evaluation(
                db,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=output_row.id,
                output=result.output,
            )
        elif cls.id == "capture.risk_register":
            await _writeback_risks(
                db,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=output_row.id,
                output=result.output,
            )
        await db.flush()

        # Knowledge-graph ingestion: every successful module contributes
        # structured facts to the workspace's institutional memory. Auxiliary
        # to the run — never let a graph hiccup fail the user's generation.
        try:
            await graph_service.ingest_module_output(
                db,
                workspace_id=workspace_id,
                opp=opp,
                module_id=cls.id,
                output=result.output,
            )
            await db.flush()
        except Exception:  # noqa: BLE001
            logger.exception(
                "knowledge-graph ingestion failed for module %s on opportunity %s",
                cls.id,
                opportunity_id,
            )

    return AIOutputResponse(
        id=output_row.id,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=output_row.module_id,
        module_version=output_row.module_version,
        status=output_row.status,  # type: ignore[arg-type]
        model_provider=output_row.model_provider,
        model_name=output_row.model_name,
        input_tokens=output_row.input_tokens,
        output_tokens=output_row.output_tokens,
        latency_ms=output_row.latency_ms,
        output_json=output_row.output_json,
        citations=build_citations(result.evidence, result.market_evidence),
        generated_at=output_row.created_at,
    )


async def latest_for_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
) -> AIOutput | None:
    stmt = (
        select(AIOutput)
        .where(AIOutput.workspace_id == workspace_id)
        .where(AIOutput.opportunity_id == opportunity_id)
        .where(AIOutput.module_id == module_id)
        .order_by(desc(AIOutput.created_at))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def history_for_module(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    limit: int = 20,
) -> list[AIOutput]:
    stmt = (
        select(AIOutput)
        .where(AIOutput.workspace_id == workspace_id)
        .where(AIOutput.opportunity_id == opportunity_id)
        .where(AIOutput.module_id == module_id)
        .order_by(desc(AIOutput.created_at))
        .limit(min(max(limit, 1), 100))
    )
    return list((await db.execute(stmt)).scalars().all())


def serialize_ai_output(row: AIOutput) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "workspace_id": str(row.workspace_id),
        "opportunity_id": str(row.opportunity_id) if row.opportunity_id else None,
        "module_id": row.module_id,
        "module_version": row.module_version,
        "status": row.status,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "latency_ms": row.latency_ms,
        "output_json": row.output_json,
        "generated_at": row.created_at.isoformat(),
    }


# ── Structured writeback helpers ──────────────────────────────────────────
# Each helper replaces all prior rows for this opportunity (per-module) with
# the freshly generated analysis so CSV exports and joins always reflect the
# latest source-cited intelligence.


async def _writeback_compliance(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    ai_output_id: uuid.UUID,
    output: dict[str, Any],
) -> None:
    await db.execute(
        delete(ComplianceRequirement).where(
            ComplianceRequirement.opportunity_id == opportunity_id
        )
    )
    rows = output.get("rows") or []
    for row in rows:
        try:
            page = row.get("source_page")
            if page is not None:
                page = int(page)
        except (TypeError, ValueError):
            page = None
        priority = row.get("customer_priority")
        if priority not in ("critical", "high", "medium", "low"):
            priority = None
        status_val = row.get("proposed_status") or "open"
        if status_val not in ("open", "in_progress", "complete", "n_a"):
            status_val = "open"
        db.add(
            ComplianceRequirement(
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=ai_output_id,
                requirement_code=(row.get("requirement_id") or "")[:80] or None,
                requirement_text=row.get("requirement_text") or "(no text)",
                source_page=page,
                source_section=(row.get("source_section") or None),
                category=(row.get("category") or None),
                owner=(row.get("response_owner") or None),
                status=status_val,
                notes=(row.get("notes") or None),
                why_requirement_exists=(row.get("why_requirement_exists") or None),
                mission_alignment=(row.get("mission_alignment") or None),
                customer_priority=priority,
            )
        )


async def _writeback_evaluation(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    ai_output_id: uuid.UUID,
    output: dict[str, Any],
) -> None:
    await db.execute(
        delete(EvaluationCriterion).where(
            EvaluationCriterion.opportunity_id == opportunity_id
        )
    )
    factors = output.get("factors") or []
    intel = output.get("evaluation_intelligence")
    drivers = output.get("likely_decision_drivers") or []
    discriminators = output.get("potential_discriminators") or []
    weaknesses = output.get("potential_weaknesses") or []
    recs = output.get("strategic_recommendations") or []
    # Insight payload is replicated on every factor row so any single
    # factor read still carries the capture intelligence.
    importance_allowed = {
        "most_important",
        "important",
        "less_important",
        "equal",
        "unspecified",
    }
    for f in factors:
        importance = f.get("importance") or "unspecified"
        if importance not in importance_allowed:
            importance = "unspecified"
        page = f.get("source_page")
        if page is not None:
            try:
                page = int(page)
            except (TypeError, ValueError):
                page = None
        db.add(
            EvaluationCriterion(
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=ai_output_id,
                factor=(f.get("factor") or "Unspecified factor")[:200],
                subfactor=(f.get("subfactor") or None),
                importance=importance,
                required_response_elements=(f.get("required_response_elements") or None),
                source_section=(f.get("source_section") or None),
                source_page=page,
                evaluation_intelligence=intel,
                likely_decision_drivers=drivers or None,
                potential_discriminators=discriminators or None,
                potential_weaknesses=weaknesses or None,
                strategic_recommendations=recs or None,
            )
        )


_PROBABILITY = {"low", "medium", "high"}
_SEVERITY = {"low", "medium", "high", "critical"}


async def _writeback_risks(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    ai_output_id: uuid.UUID,
    output: dict[str, Any],
) -> None:
    await db.execute(delete(Risk).where(Risk.opportunity_id == opportunity_id))
    lane_payloads = (
        ("capture", output.get("capture_risks") or []),
        ("proposal", output.get("proposal_risks") or []),
        ("delivery", output.get("delivery_risks") or []),
        ("customer", output.get("customer_risks") or []),
    )
    for lane, items in lane_payloads:
        for item in items:
            probability = item.get("probability") or "medium"
            if probability not in _PROBABILITY:
                probability = "medium"
            severity = item.get("severity") or "medium"
            if severity not in _SEVERITY:
                severity = "medium"
            db.add(
                Risk(
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    ai_output_id=ai_output_id,
                    title=(item.get("title") or "(untitled risk)")[:300],
                    description=(item.get("description") or None),
                    mitigation=(item.get("mitigation") or None),
                    owner=(item.get("owner") or None),
                    status="open",
                    lane=lane,
                    mission_impact=(item.get("mission_impact") or None),
                    probability=probability,
                    severity=severity,
                    supporting_evidence=(item.get("supporting_evidence") or None),
                )
            )
