"""Shared helpers for Apex Federal demo seeding."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph import service as graph_service
from app.intelligence.registry import get_registry
from app.models import (
    AIOutput,
    AssumptionValidation,
    AutomationRun,
    Comment,
    Connector,
    ConnectorSyncJob,
    DeliverableReview,
    Document,
    GraphEntity,
    HumanOverride,
    Opportunity,
    ProposalAsset,
    ProposalAssetCitation,
    ProposalAssetUsage,
    PursuitOutcome,
    ReviewEvent,
    User,
)
from app.schemas.outcome import OutcomeRecordRequest
from app.services import outcome_intelligence_service
from app.services.proposal_repository_service import (
    asset_normalized_key,
    recompute_asset_outcomes,
)
from app.storage import get_blob_store
from seeds.apex.constants import PursuitSpec
from seeds.apex.payloads import build_payload


async def upsert_ai_output(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity: Opportunity,
    module_id: str,
    user_id: uuid.UUID,
    created_at: datetime | None = None,
) -> AIOutput:
    registry = get_registry()
    cls = registry.get(module_id)
    if cls is None:
        raise ValueError(f"Unknown module: {module_id}")

    pursuit = _pursuit_from_opp(opportunity)
    payload = build_payload(module_id, pursuit)

    existing = (
        await db.execute(
            select(AIOutput)
            .where(AIOutput.opportunity_id == opportunity.id)
            .where(AIOutput.module_id == module_id)
            .order_by(AIOutput.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    row = AIOutput(
        workspace_id=workspace_id,
        opportunity_id=opportunity.id,
        module_id=cls.id,
        module_version=cls.version,
        prompt_id=cls.prompt_id,
        prompt_version=cls.prompt_version,
        model_provider="missioniq",
        model_name="demo-seed",
        input_tokens=0,
        output_tokens=0,
        latency_ms=12,
        output_json=payload,
        status="ok",
        generated_by_user_id=user_id,
    )
    if created_at:
        row.created_at = created_at
        row.updated_at = created_at
    db.add(row)
    await db.flush()
    try:
        await graph_service.ingest_module_output(
            db,
            workspace_id=workspace_id,
            opp=opportunity,
            module_id=cls.id,
            output=payload,
        )
    except Exception:  # noqa: BLE001
        pass
    return row


def _pursuit_from_opp(opp: Opportunity) -> PursuitSpec:
    from seeds.apex.constants import SHOWCASE_PURSUITS

    for p in SHOWCASE_PURSUITS:
        if p.solicitation_number == opp.solicitation_number:
            return p
    return PursuitSpec(
        key="generic",
        solicitation_number=opp.solicitation_number or "GENERIC",
        name=opp.name,
        agency=opp.agency or "Federal Agency",
        sub_agency=opp.sub_agency or "",
        value_cents=opp.estimated_value_cents or 0,
        capture_stage=opp.capture_stage,
        outcome=None,
        themes=["Service delivery"],
    )


async def seed_intelligence_for_pursuit(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity: Opportunity,
    user_id: uuid.UUID,
    modules: list[str],
    include_outcome_intel: bool = False,
    base_time: datetime | None = None,
) -> dict[str, AIOutput]:
    outputs: dict[str, AIOutput] = {}
    t = base_time or datetime.now(UTC)
    for i, mid in enumerate(modules):
        outputs[mid] = await upsert_ai_output(
            db,
            workspace_id=workspace_id,
            opportunity=opportunity,
            module_id=mid,
            user_id=user_id,
            created_at=t + timedelta(minutes=i),
        )
    if include_outcome_intel:
        outputs["capture.outcome_intelligence"] = await upsert_ai_output(
            db,
            workspace_id=workspace_id,
            opportunity=opportunity,
            module_id="capture.outcome_intelligence",
            user_id=user_id,
            created_at=t + timedelta(minutes=len(modules)),
        )
    return outputs


async def record_pursuit_outcome(
    db: AsyncSession,
    *,
    opportunity: Opportunity,
    outcome: str,
    user_id: uuid.UUID,
    value_cents: int | None = None,
    factors: list[str] | None = None,
    debrief: str | None = None,
    competitor: str | None = None,
) -> PursuitOutcome:
    existing = await outcome_intelligence_service.get_outcome(
        db, opportunity_id=opportunity.id
    )
    if existing:
        return existing
    return await outcome_intelligence_service.record_outcome(
        db,
        opportunity=opportunity,
        payload=OutcomeRecordRequest(
            outcome=outcome,  # type: ignore[arg-type]
            decided_at=datetime.now(UTC) - timedelta(days=30),
            awarded_value_cents=value_cents,
            awarded_to_competitor=competitor,
            outcome_factors=factors or [],
            debrief_notes=debrief,
        ),
        user_id=user_id,
    )


async def ensure_proposal_document(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
) -> Document:
    existing = (
        await db.execute(
            select(Document)
            .where(Document.opportunity_id == opportunity_id)
            .where(Document.name == filename)
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    body = (
        f"SYNTHETIC PROPOSAL VOLUME — {filename}\n\n"
        "SECTION 1: EXECUTIVE SUMMARY\n"
        "Apex Federal Solutions proposes a zero-disruption transition with "
        "omnichannel citizen experience and AI-enabled self-service.\n\n"
        "SECTION 2: TRANSITION APPROACH\n"
        "90-day phased transition with shadow period and parallel operations.\n\n"
        "SECTION 3: STAFFING APPROACH\n"
        "Blended onshore/nearshore contact center model with tiered service desk.\n\n"
        "SECTION 4: PAST PERFORMANCE\n"
        "CMS Citizen Engagement and VBA Benefits Experience — relevant federal CX.\n"
    ).encode()
    doc_id = uuid.uuid4()
    blob = get_blob_store()
    key = await blob.write(
        workspace_id=workspace_id,
        document_id=doc_id,
        data=body,
        filename=filename,
    )
    doc = Document(
        id=doc_id,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        name=filename,
        doc_type="proposal",
        mime_type="text/plain",
        size_bytes=len(body),
        blob_key=key,
        sha256=hashlib.sha256(body).hexdigest(),
        status="ready",
        progress_pct=100,
        page_count=12,
        chunk_count=4,
        uploaded_by_user_id=user_id,
        uploaded_at=datetime.now(UTC) - timedelta(days=90),
    )
    db.add(doc)
    await db.flush()
    return doc


async def seed_proposal_assets(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    assets: list[dict[str, Any]],
    doc: Document,
    opportunity_map: dict[str, uuid.UUID],
    user_id: uuid.UUID,
) -> None:
    for spec in assets:
        nkey = asset_normalized_key(spec["asset_type"], spec["title"])
        existing = (
            await db.execute(
                select(ProposalAsset)
                .where(ProposalAsset.workspace_id == workspace_id)
                .where(ProposalAsset.normalized_key == nkey)
            )
        ).scalar_one_or_none()
        if existing:
            continue

        opp_id = None
        agency_tokens = spec.get("agency", "").split()
        agency_prefix = agency_tokens[0] if agency_tokens else ""
        for sol, oid in opportunity_map.items():
            if (agency_prefix and agency_prefix in sol) or spec["title"] in sol:
                opp_id = oid
                break
        if opp_id is None and opportunity_map:
            opp_id = next(iter(opportunity_map.values()))

        asset = ProposalAsset(
            workspace_id=workspace_id,
            asset_type=spec["asset_type"],
            title=spec["title"],
            summary=(
                f"Reusable {spec['asset_type'].replace('_', ' ')} from Apex federal "
                f"proposals — {spec['title']}."
            ),
            content={"narrative": spec["title"]},
            document_id=doc.id,
            opportunity_id=opp_id,
            agency=spec.get("agency"),
            author="Jennifer Carter",
            version="v1",
            source_type="user_upload",
            tags=[spec["asset_type"], "demo"],
            extraction_confidence="high",
            extraction_basis="evidence",
            normalized_key=nkey,
            wins=3,
            losses=1,
            usage_count=5,
            win_rate=0.75,
            outcome_weight=0.667,
            submission_date=datetime.now(UTC) - timedelta(days=120),
        )
        db.add(asset)
        await db.flush()
        db.add(
            ProposalAssetCitation(
                asset_id=asset.id,
                document_id=doc.id,
                page_start=1,
                page_end=2,
                excerpt=f"Supporting excerpt for {spec['title']}.",
            )
        )
        for opp_key, oid in list(opportunity_map.items())[:3]:
            db.add(
                ProposalAssetUsage(
                    workspace_id=workspace_id,
                    asset_id=asset.id,
                    opportunity_id=oid,
                    usage_kind="extracted_from",
                )
            )
    await recompute_asset_outcomes(db, workspace_id=workspace_id)


async def seed_governance_activity(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    outputs: dict[str, AIOutput],
    users: dict[str, User],
) -> None:
    win_out = outputs.get("capture.win_strategy")
    brief_out = outputs.get("capture.executive_brief")
    if win_out is None:
        return

    existing_comment = (
        await db.execute(
            select(Comment)
            .where(Comment.opportunity_id == opportunity_id)
            .where(Comment.target_module_id == "capture.win_strategy")
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing_comment is None:
        db.add(
            Comment(
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                target_module_id="capture.win_strategy",
                ai_output_id=win_out.id,
                body=(
                    "Strong transition narrative — validate staffing numbers against "
                    "the NEOA program office before gate review."
                ),
                author_user_id=users["david.kim@apexfederal.demo"].id,
                status="open",
            )
        )
        db.add(
            Comment(
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                target_module_id="capture.executive_brief",
                ai_output_id=brief_out.id if brief_out else win_out.id,
                body="Executive recommendation aligns with capture director guidance.",
                author_user_id=users["jennifer.carter@apexfederal.demo"].id,
                status="resolved",
                resolved_by_user_id=users["michael.reynolds@apexfederal.demo"].id,
                resolved_at=datetime.now(UTC) - timedelta(days=2),
            )
        )

    review = (
        await db.execute(
            select(DeliverableReview)
            .where(DeliverableReview.opportunity_id == opportunity_id)
            .where(DeliverableReview.module_id == "capture.win_strategy")
        )
    ).scalar_one_or_none()
    if review is None:
        review = DeliverableReview(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            module_id="capture.win_strategy",
            ai_output_id=win_out.id,
            status="approved",
        )
        db.add(review)
        await db.flush()
        db.add(
            ReviewEvent(
                review_id=review.id,
                action="submitted",
                decision_summary="Submitted for capture director review",
                actor_user_id=users["jennifer.carter@apexfederal.demo"].id,
                created_at=datetime.now(UTC) - timedelta(days=5),
            )
        )
        db.add(
            ReviewEvent(
                review_id=review.id,
                action="approved",
                decision_summary="Pursue with conditions — strong CX fit",
                notes="Approved for gate review package.",
                actor_user_id=users["michael.reynolds@apexfederal.demo"].id,
                created_at=datetime.now(UTC) - timedelta(days=3),
            )
        )

    override_exists = (
        await db.execute(
            select(HumanOverride)
            .where(HumanOverride.opportunity_id == opportunity_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if override_exists is None:
        db.add(
            HumanOverride(
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                ai_output_id=win_out.id,
                module_id="capture.win_strategy",
                override_type="score",
                field="win_confidence_assessment.score",
                original_value={"score": 58},
                override_value={"score": 65},
                reason="Capture director adjustment based on recent CMS win pattern.",
                created_by_user_id=users["michael.reynolds@apexfederal.demo"].id,
                created_at=datetime.now(UTC) - timedelta(days=2),
            )
        )

    if brief_out:
        val_exists = (
            await db.execute(
                select(AssumptionValidation)
                .where(AssumptionValidation.ai_output_id == brief_out.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if val_exists is None:
            db.add(
                AssumptionValidation(
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    ai_output_id=brief_out.id,
                    module_id="capture.executive_brief",
                    assumption_key=hashlib.sha256(b"assumption:transition").hexdigest(),
                    assumption_text="Incumbent will not aggressively price to retain.",
                    status="validated",
                    notes="Confirmed via market intelligence and CO feedback.",
                    validator_user_id=users["michael.reynolds@apexfederal.demo"].id,
                    created_at=datetime.now(UTC) - timedelta(days=1),
                )
            )


async def seed_connectors(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    opportunity_id: uuid.UUID | None,
) -> dict[str, Connector]:
    specs = [
        ("salesforce", "crm", "Salesforce CRM"),
        ("sharepoint", "document_repository", "SharePoint Pursuit Library"),
        ("local_repository", "document_repository", "Local Proposal Archive"),
    ]
    out: dict[str, Connector] = {}
    now = datetime.now(UTC)
    for pid, ctype, label in specs:
        existing = (
            await db.execute(
                select(Connector)
                .where(Connector.workspace_id == workspace_id)
                .where(Connector.provider_id == pid)
            )
        ).scalar_one_or_none()
        if existing:
            out[pid] = existing
            continue
        conn = Connector(
            workspace_id=workspace_id,
            provider_id=pid,
            connector_type=ctype,
            name=label,
            status="connected",
            config={"demo": True},
            auto_create_pursuits=pid == "salesforce",
            auto_run_automation=False,
            last_sync_at=now - timedelta(hours=6),
            last_success_at=now - timedelta(hours=6),
            created_by_user_id=user_id,
        )
        db.add(conn)
        await db.flush()
        job = ConnectorSyncJob(
            connector_id=conn.id,
            workspace_id=workspace_id,
            trigger="manual",
            status="succeeded",
            progress_pct=100,
            stats={
                "items_discovered": 12,
                "opportunities_created": 2,
                "documents_ingested": 4,
            },
            started_at=now - timedelta(hours=6, minutes=5),
            finished_at=now - timedelta(hours=6),
            triggered_by_user_id=user_id,
        )
        db.add(job)
        if opportunity_id and pid == "salesforce":
            db.add(
                AutomationRun(
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    trigger="connector",
                    status="succeeded",
                    current_step=None,
                    steps=[
                        {"step_id": "customer_dna", "label": "Customer DNA", "status": "succeeded"},
                        {"step_id": "company_dna", "label": "Company DNA", "status": "succeeded"},
                        {"step_id": "win_strategy", "label": "Win Strategy", "status": "succeeded"},
                        {"step_id": "executive_brief", "label": "Executive Brief", "status": "succeeded"},
                    ],
                    started_at=now - timedelta(hours=5),
                    finished_at=now - timedelta(hours=4, minutes=30),
                    triggered_by_user_id=user_id,
                    connector_sync_job_id=job.id,
                )
            )
        out[pid] = conn
    return out


async def seed_graph_extras(db: AsyncSession, *, workspace_id: uuid.UUID) -> None:
    """Supplement graph with competitors and technologies for richer demo stats."""
    extras = [
        ("competitor", "Vector Systems Group"),
        ("competitor", "Horizon Digital Partners"),
        ("competitor", "Pinnacle Operations LLC"),
        ("technology", "Salesforce Service Cloud"),
        ("technology", "Genesys Cloud CX"),
        ("contract_vehicle", "GSA MAS"),
        ("contract_vehicle", "OASIS+"),
    ]
    for etype, name in extras:
        from app.graph.extract import normalize_key

        nkey = normalize_key(name)
        exists = (
            await db.execute(
                select(GraphEntity)
                .where(GraphEntity.workspace_id == workspace_id)
                .where(GraphEntity.entity_type == etype)
                .where(GraphEntity.normalized_key == nkey)
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            GraphEntity(
                workspace_id=workspace_id,
                entity_type=etype,
                name=name,
                normalized_key=nkey,
                attributes={},
                mention_count=3,
                wins=2,
                losses=1,
                outcome_weight=0.6,
            )
        )
