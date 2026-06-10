"""Collaboration & Governance service.

MissionIQ generates intelligence; humans make decisions. This service is the
single mutation path for the governance layer — comments, the review/approval
state machine, human overrides (decision ledger + feedback capture),
assumption validation, and institutional-memory signals.

Invariants enforced here:

- ``ai_output`` rows are never written — original AI intelligence is
  preserved by construction.
- ``review_event``, ``human_override``, ``assumption_validation``, and
  ``governance_signal`` are append-only: no update/delete functions exist.
- Comments are body-immutable; only their open/resolved status toggles.
- Every mutation writes an audit record in the same transaction.
- Governance signals are collected and stored only; recommendation logic,
  prompts, and Knowledge Graph weighting do not consume them yet.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.rbac import require_capability
from app.models import (
    AIOutput,
    AssumptionValidation,
    Comment,
    DeliverableReview,
    GovernanceSignal,
    HumanOverride,
    PursuitOutcome,
    ReviewEvent,
    User,
)
from app.models.governance import GOVERNED_MODULES, REVIEWABLE_MODULES
from app.schemas.governance import (
    AssumptionItem,
    AssumptionPanel,
    AssumptionValidateRequest,
    AssumptionValidationRecord,
    CommentCreate,
    CommentResponse,
    DecisionHistoryResponse,
    DecisionTimelineEntry,
    OverrideCreate,
    OverrideResponse,
    ReviewEventResponse,
    ReviewResponse,
)
from app.services.audit_service import write_audit
from app.services.outcome_intelligence_service import extract_recommendation

# ── Review state machine (pure) ──────────────────────────────────────────────

# action → (allowed source states, resulting state, event action, capability)
REVIEW_TRANSITIONS: dict[str, tuple[tuple[str, ...], str, str, str]] = {
    "submit": (("draft", "rejected"), "in_review", "submitted", "review.submit"),
    "approve": (("in_review",), "approved", "approved", "review.decide"),
    "reject": (("in_review",), "rejected", "rejected", "review.decide"),
    "reopen": (("approved", "rejected"), "in_review", "reopened", "review.decide"),
    "archive": (
        ("draft", "in_review", "approved", "rejected"),
        "archived",
        "archived",
        "review.submit",
    ),
}


def apply_review_action(status: str, action: str) -> tuple[str, str]:
    """Pure transition: (current status, action) → (new status, event action).

    Raises ``ConflictError`` for illegal transitions so review history can
    never contain an impossible sequence.
    """
    spec = REVIEW_TRANSITIONS.get(action)
    if spec is None:
        raise ConflictError(f"Unknown review action: {action}", code="review.unknown_action")
    allowed, new_status, event_action, _capability = spec
    if status not in allowed:
        raise ConflictError(
            f"Cannot {action} a deliverable in '{status}' state.",
            code="review.illegal_transition",
        )
    return new_status, event_action


def review_capability(action: str) -> str:
    spec = REVIEW_TRANSITIONS.get(action)
    if spec is None:
        raise ConflictError(f"Unknown review action: {action}", code="review.unknown_action")
    return spec[3]


def decision_summary_for(module_id: str, output: dict) -> str | None:
    """Snapshot the deliverable's recommendation (e.g. "pursue_aggressively")
    so approval records are self-contained even if the output is superseded."""
    snap = extract_recommendation(module_id, output)
    if snap is None:
        return None
    parts: list[str] = []
    if snap.predicted_label:
        parts.append(str(snap.predicted_label).replace("_", " ").title())
    if snap.predicted_score is not None:
        parts.append(f"{round(snap.predicted_score)}% confidence")
    return " · ".join(parts) or None


# ── Assumption extraction (pure) ─────────────────────────────────────────────

# Preferred display-text fields on objects tagged basis="assumption".
_TEXT_FIELDS = (
    "statement",
    "text",
    "title",
    "competitor_move",
    "action",
    "rationale",
    "positioning",
    "description",
)


def assumption_key(path: str, text: str) -> str:
    """Stable identity for an assumption within one generation: sha256 of the
    index-free path plus normalized text, so reordering does not re-key."""
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(f"{path}|{normalized}".encode()).hexdigest()


def _display_text(obj: dict) -> str | None:
    name = obj.get("name")
    for field in _TEXT_FIELDS:
        value = obj.get(field)
        if isinstance(value, str) and value.strip():
            if field == "rationale" and isinstance(name, str) and name.strip():
                return f"{name}: {value}"
            return value
    if isinstance(name, str) and name.strip():
        return name
    return None


def extract_assumptions(output: Any, path: str = "") -> list[tuple[str, str, str]]:
    """Walk an output_json tree and collect every statement the AI tagged
    ``basis: "assumption"`` as (key, text, path) tuples.

    List indices are excluded from paths so keys survive reordering; modules
    without basis tags simply yield nothing (honest empty state).
    """
    found: list[tuple[str, str, str]] = []
    if isinstance(output, dict):
        if output.get("basis") == "assumption":
            text = _display_text(output)
            if text:
                found.append((assumption_key(path, text), text, path))
        for k, v in output.items():
            child = f"{path}.{k}" if path else k
            found.extend(extract_assumptions(v, child))
    elif isinstance(output, list):
        for item in output:
            found.extend(extract_assumptions(item, path))
    # De-duplicate identical (path, text) pairs while preserving order.
    seen: set[str] = set()
    unique: list[tuple[str, str, str]] = []
    for key, text, p in found:
        if key not in seen:
            seen.add(key)
            unique.append((key, text, p))
    return unique


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _user_names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {u.id: u.full_name for u in rows}


async def _latest_output(
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


def _require_governed(module_id: str) -> None:
    if module_id not in GOVERNED_MODULES:
        raise NotFoundError(
            f"Module '{module_id}' does not support governance.",
            code="governance.module_not_governed",
        )


def _emit_signal(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    signal_type: str,
    subject: str,
    opportunity_id: uuid.UUID | None,
    module_id: str | None,
    actor_user_id: uuid.UUID | None,
    payload: dict | None = None,
) -> None:
    """Append an institutional-memory signal (collected only, never consumed
    by recommendation logic in this milestone)."""
    db.add(
        GovernanceSignal(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            module_id=module_id,
            signal_type=signal_type,
            subject=subject,
            payload=payload or {},
            actor_user_id=actor_user_id,
        )
    )


# ── Comments ─────────────────────────────────────────────────────────────────


def _comment_response(c: Comment, names: dict[uuid.UUID, str]) -> CommentResponse:
    return CommentResponse(
        id=c.id,
        opportunity_id=c.opportunity_id,
        target_module_id=c.target_module_id,
        ai_output_id=c.ai_output_id,
        parent_comment_id=c.parent_comment_id,
        body=c.body,
        mentions=list(c.mentions or []),
        status=c.status,  # type: ignore[arg-type]
        author_user_id=c.author_user_id,
        author_name=names.get(c.author_user_id, "Unknown"),
        resolved_by_user_id=c.resolved_by_user_id,
        resolved_by_name=names.get(c.resolved_by_user_id) if c.resolved_by_user_id else None,
        resolved_at=c.resolved_at,
        created_at=c.created_at,
    )


async def create_comment(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    actor: User,
    actor_role: str,
    payload: CommentCreate,
) -> CommentResponse:
    require_capability(actor_role, "comment.create")
    _require_governed(payload.target_module_id)
    parent: Comment | None = None
    if payload.parent_comment_id is not None:
        parent = await db.get(Comment, payload.parent_comment_id)
        if parent is None or parent.opportunity_id != opportunity_id:
            raise NotFoundError("Parent comment not found.", code="comment.parent_not_found")
        if parent.parent_comment_id is not None:
            raise ConflictError(
                "Replies are one level deep — reply to the thread root.",
                code="comment.reply_depth",
            )
    latest = await _latest_output(
        db,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        module_id=payload.target_module_id,
    )
    comment = Comment(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        target_module_id=payload.target_module_id,
        ai_output_id=latest.id if latest else None,
        parent_comment_id=payload.parent_comment_id,
        body=payload.body,
        mentions=payload.mentions or None,
        status="open",
        author_user_id=actor.id,
    )
    db.add(comment)
    await db.flush()
    await write_audit(
        db,
        action="comment.replied" if parent is not None else "comment.created",
        workspace_id=workspace_id,
        actor_user_id=actor.id,
        target_type="comment",
        target_id=comment.id,
        meta={
            "module_id": payload.target_module_id,
            "opportunity_id": str(opportunity_id),
            "parent_comment_id": str(payload.parent_comment_id)
            if payload.parent_comment_id
            else None,
            "mentions": [str(m) for m in payload.mentions],
        },
    )
    names = await _user_names(db, {comment.author_user_id})
    return _comment_response(comment, names)


async def set_comment_status(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    comment_id: uuid.UUID,
    actor: User,
    actor_role: str,
    resolved: bool,
) -> CommentResponse:
    require_capability(actor_role, "comment.resolve")
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.opportunity_id != opportunity_id:
        raise NotFoundError("Comment not found.", code="comment.not_found")
    if comment.parent_comment_id is not None:
        raise ConflictError(
            "Resolve the thread root, not a reply.", code="comment.resolve_reply"
        )
    if resolved:
        comment.status = "resolved"
        comment.resolved_by_user_id = actor.id
        comment.resolved_at = datetime.now(UTC)
        _emit_signal(
            db,
            workspace_id=workspace_id,
            signal_type="comment_resolved",
            subject=comment.body[:300],
            opportunity_id=opportunity_id,
            module_id=comment.target_module_id,
            actor_user_id=actor.id,
            payload={"comment_id": str(comment.id)},
        )
    else:
        comment.status = "open"
        comment.resolved_by_user_id = None
        comment.resolved_at = None
    await write_audit(
        db,
        action="comment.resolved" if resolved else "comment.reopened",
        workspace_id=workspace_id,
        actor_user_id=actor.id,
        target_type="comment",
        target_id=comment.id,
        meta={"module_id": comment.target_module_id, "opportunity_id": str(opportunity_id)},
    )
    ids = {comment.author_user_id}
    if comment.resolved_by_user_id:
        ids.add(comment.resolved_by_user_id)
    names = await _user_names(db, ids)
    return _comment_response(comment, names)


async def list_comments(
    db: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    module_id: str | None = None,
) -> list[CommentResponse]:
    stmt = (
        select(Comment)
        .where(Comment.opportunity_id == opportunity_id)
        .order_by(Comment.created_at.asc())
    )
    if module_id:
        stmt = stmt.where(Comment.target_module_id == module_id)
    comments = list((await db.execute(stmt)).scalars().all())
    ids: set[uuid.UUID] = set()
    for c in comments:
        ids.add(c.author_user_id)
        if c.resolved_by_user_id:
            ids.add(c.resolved_by_user_id)
    names = await _user_names(db, ids)
    return [_comment_response(c, names) for c in comments]


# ── Review workflow ──────────────────────────────────────────────────────────


def _review_response(
    review: DeliverableReview,
    events: list[ReviewEvent],
    names: dict[uuid.UUID, str],
    generated_at,
) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        opportunity_id=review.opportunity_id,
        module_id=review.module_id,
        ai_output_id=review.ai_output_id,
        status=review.status,  # type: ignore[arg-type]
        generated_at=generated_at,
        events=[
            ReviewEventResponse(
                id=e.id,
                action=e.action,  # type: ignore[arg-type]
                decision_summary=e.decision_summary,
                notes=e.notes,
                actor_user_id=e.actor_user_id,
                actor_name=names.get(e.actor_user_id) if e.actor_user_id else None,
                created_at=e.created_at,
            )
            for e in events
        ],
    )


async def _active_review(
    db: AsyncSession, opportunity_id: uuid.UUID, module_id: str
) -> DeliverableReview | None:
    stmt = (
        select(DeliverableReview)
        .where(DeliverableReview.opportunity_id == opportunity_id)
        .where(DeliverableReview.module_id == module_id)
        .where(DeliverableReview.status != "archived")
        .order_by(desc(DeliverableReview.created_at))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_or_create_review(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
) -> ReviewResponse:
    """Return the active review cycle for the latest generation.

    Lazily creates a draft cycle; if the deliverable was regenerated since
    the active cycle began, that cycle is archived (with an event noting the
    supersession) and a fresh draft starts — an approval can never silently
    refer to content that changed.
    """
    if module_id not in REVIEWABLE_MODULES:
        raise NotFoundError(
            f"Module '{module_id}' does not go through review.",
            code="review.module_not_reviewable",
        )
    latest = await _latest_output(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )
    if latest is None:
        raise NotFoundError(
            "Generate the deliverable before opening a review.",
            code="review.no_output",
        )
    review = await _active_review(db, opportunity_id, module_id)
    if review is not None and review.ai_output_id != latest.id:
        review.status = "archived"
        db.add(
            ReviewEvent(
                review_id=review.id,
                action="archived",
                notes="Superseded by regeneration of the deliverable.",
                actor_user_id=None,
            )
        )
        review = None
    if review is None:
        review = DeliverableReview(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            module_id=module_id,
            ai_output_id=latest.id,
            status="draft",
        )
        db.add(review)
        await db.flush()
    events = list(
        (
            await db.execute(
                select(ReviewEvent)
                .where(ReviewEvent.review_id == review.id)
                .order_by(ReviewEvent.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    names = await _user_names(db, {e.actor_user_id for e in events if e.actor_user_id})
    return _review_response(review, events, names, latest.created_at)


async def act_on_review(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    actor: User,
    actor_role: str,
    action: str,
    notes: str | None,
) -> ReviewResponse:
    require_capability(actor_role, review_capability(action))
    # Ensure the cycle is bound to the latest generation before transitioning.
    await get_or_create_review(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )
    review = await _active_review(db, opportunity_id, module_id)
    assert review is not None
    new_status, event_action = apply_review_action(review.status, action)

    decision_summary: str | None = None
    latest = await _latest_output(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )
    if action in ("approve", "reject") and latest is not None:
        decision_summary = decision_summary_for(module_id, latest.output_json)

    review.status = new_status
    db.add(
        ReviewEvent(
            review_id=review.id,
            action=event_action,
            decision_summary=decision_summary,
            notes=notes,
            actor_user_id=actor.id,
        )
    )
    await write_audit(
        db,
        action=f"review.{event_action}",
        workspace_id=workspace_id,
        actor_user_id=actor.id,
        target_type="deliverable_review",
        target_id=review.id,
        meta={
            "module_id": module_id,
            "opportunity_id": str(opportunity_id),
            "ai_output_id": str(review.ai_output_id) if review.ai_output_id else None,
            "decision_summary": decision_summary,
            "notes": notes,
        },
    )
    if action in ("approve", "reject"):
        _emit_signal(
            db,
            workspace_id=workspace_id,
            signal_type=f"review_{event_action}",
            subject=f"{module_id} {event_action}"
            + (f" — {decision_summary}" if decision_summary else ""),
            opportunity_id=opportunity_id,
            module_id=module_id,
            actor_user_id=actor.id,
            payload={"review_id": str(review.id), "notes": notes},
        )
    return await get_or_create_review(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )


async def review_history(
    db: AsyncSession, *, opportunity_id: uuid.UUID, module_id: str
) -> list[ReviewResponse]:
    """All review cycles (including archived) — history is never overwritten."""
    stmt = (
        select(DeliverableReview)
        .where(DeliverableReview.opportunity_id == opportunity_id)
        .where(DeliverableReview.module_id == module_id)
        .order_by(desc(DeliverableReview.created_at))
    )
    reviews = list((await db.execute(stmt)).scalars().all())
    out: list[ReviewResponse] = []
    for review in reviews:
        events = list(
            (
                await db.execute(
                    select(ReviewEvent)
                    .where(ReviewEvent.review_id == review.id)
                    .order_by(ReviewEvent.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        names = await _user_names(db, {e.actor_user_id for e in events if e.actor_user_id})
        generated_at = None
        if review.ai_output_id:
            output = await db.get(AIOutput, review.ai_output_id)
            generated_at = output.created_at if output else None
        out.append(_review_response(review, events, names, generated_at))
    return out


# ── Human overrides (decision ledger + feedback capture) ─────────────────────


def _override_response(o: HumanOverride, names: dict[uuid.UUID, str]) -> OverrideResponse:
    return OverrideResponse(
        id=o.id,
        opportunity_id=o.opportunity_id,
        ai_output_id=o.ai_output_id,
        module_id=o.module_id,
        override_type=o.override_type,  # type: ignore[arg-type]
        field=o.field,
        original_value=(o.original_value or {}).get("value"),
        override_value=(o.override_value or {}).get("value"),
        reason=o.reason,
        created_by_user_id=o.created_by_user_id,
        created_by_name=names.get(o.created_by_user_id) if o.created_by_user_id else None,
        created_at=o.created_at,
    )


async def create_override(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    actor: User,
    actor_role: str,
    payload: OverrideCreate,
) -> OverrideResponse:
    require_capability(actor_role, "decision.override")
    _require_governed(payload.module_id)
    latest = await _latest_output(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=payload.module_id
    )
    override = HumanOverride(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        ai_output_id=latest.id if latest else None,
        module_id=payload.module_id,
        override_type=payload.override_type,
        field=payload.field,
        # JSONB envelope so scalars (62, "no_bid") round-trip losslessly.
        original_value={"value": payload.original_value},
        override_value={"value": payload.override_value},
        reason=payload.reason,
        created_by_user_id=actor.id,
    )
    db.add(override)
    await db.flush()
    action = (
        "decision.overridden" if payload.override_type == "decision" else "score.overridden"
    )
    await write_audit(
        db,
        action=action,
        workspace_id=workspace_id,
        actor_user_id=actor.id,
        target_type="human_override",
        target_id=override.id,
        meta={
            "module_id": payload.module_id,
            "opportunity_id": str(opportunity_id),
            "field": payload.field,
            "original_value": payload.original_value,
            "override_value": payload.override_value,
            "reason": payload.reason,
        },
    )
    _emit_signal(
        db,
        workspace_id=workspace_id,
        signal_type=f"{payload.override_type}_overridden",
        subject=f"{payload.module_id}: {payload.field}",
        opportunity_id=opportunity_id,
        module_id=payload.module_id,
        actor_user_id=actor.id,
        payload={
            "original_value": payload.original_value,
            "override_value": payload.override_value,
            "reason": payload.reason,
        },
    )
    names = await _user_names(db, {actor.id})
    return _override_response(override, names)


async def list_overrides(
    db: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    module_id: str | None = None,
) -> list[OverrideResponse]:
    stmt = (
        select(HumanOverride)
        .where(HumanOverride.opportunity_id == opportunity_id)
        .order_by(desc(HumanOverride.created_at))
    )
    if module_id:
        stmt = stmt.where(HumanOverride.module_id == module_id)
    overrides = list((await db.execute(stmt)).scalars().all())
    names = await _user_names(
        db, {o.created_by_user_id for o in overrides if o.created_by_user_id}
    )
    return [_override_response(o, names) for o in overrides]


# ── Assumption validation ────────────────────────────────────────────────────


async def assumption_panel(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
) -> AssumptionPanel:
    """Assumptions extracted from the latest generation, merged with human
    judgments. No validation rows ⇒ honest 'unvalidated' default."""
    _require_governed(module_id)
    latest = await _latest_output(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )
    if latest is None:
        return AssumptionPanel(module_id=module_id, ai_output_id=None, assumptions=[])
    extracted = extract_assumptions(latest.output_json)
    validations = list(
        (
            await db.execute(
                select(AssumptionValidation)
                .where(AssumptionValidation.ai_output_id == latest.id)
                .order_by(AssumptionValidation.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    names = await _user_names(
        db, {v.validator_user_id for v in validations if v.validator_user_id}
    )
    by_key: dict[str, list[AssumptionValidationRecord]] = {}
    for v in validations:
        by_key.setdefault(v.assumption_key, []).append(
            AssumptionValidationRecord(
                id=v.id,
                status=v.status,  # type: ignore[arg-type]
                notes=v.notes,
                validator_user_id=v.validator_user_id,
                validator_name=names.get(v.validator_user_id)
                if v.validator_user_id
                else None,
                created_at=v.created_at,
            )
        )
    items: list[AssumptionItem] = []
    for key, text, path in extracted:
        history = by_key.get(key, [])
        latest_record = history[-1] if history else None
        items.append(
            AssumptionItem(
                key=key,
                text=text,
                path=path,
                status=latest_record.status if latest_record else "unvalidated",
                latest=latest_record,
                history=history,
            )
        )
    return AssumptionPanel(
        module_id=module_id, ai_output_id=latest.id, assumptions=items
    )


async def validate_assumption(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    module_id: str,
    actor: User,
    actor_role: str,
    payload: AssumptionValidateRequest,
) -> AssumptionPanel:
    require_capability(actor_role, "assumption.validate")
    _require_governed(module_id)
    latest = await _latest_output(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )
    if latest is None:
        raise NotFoundError("No generation to validate against.", code="assumption.no_output")
    extracted = {key: (text, path) for key, text, path in extract_assumptions(latest.output_json)}
    if payload.key not in extracted:
        raise NotFoundError(
            "Assumption not found in the latest generation.",
            code="assumption.not_found",
        )
    text, _path = extracted[payload.key]
    db.add(
        AssumptionValidation(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            ai_output_id=latest.id,
            module_id=module_id,
            assumption_key=payload.key,
            assumption_text=text,
            status=payload.status,
            notes=payload.notes,
            validator_user_id=actor.id,
        )
    )
    await write_audit(
        db,
        action=f"assumption.{payload.status}",
        workspace_id=workspace_id,
        actor_user_id=actor.id,
        target_type="ai_output",
        target_id=latest.id,
        meta={
            "module_id": module_id,
            "opportunity_id": str(opportunity_id),
            "assumption_key": payload.key,
            "assumption_text": text,
            "notes": payload.notes,
        },
    )
    _emit_signal(
        db,
        workspace_id=workspace_id,
        signal_type=f"assumption_{payload.status}",
        subject=text,
        opportunity_id=opportunity_id,
        module_id=module_id,
        actor_user_id=actor.id,
        payload={"assumption_key": payload.key, "notes": payload.notes},
    )
    return await assumption_panel(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id, module_id=module_id
    )


# ── Decision history timeline ────────────────────────────────────────────────

_MODULE_LABELS = {
    "capture.customer_dna": "Customer DNA",
    "capture.company_dna": "Company DNA",
    "capture.capability_match": "Capability Match",
    "capture.win_strategy": "Win Strategy",
    "capture.executive_brief": "Executive Brief",
    "capture.gate_review": "Gate Review",
    "capture.bid_decision": "Bid Decision",
    "capture.outcome_intelligence": "Outcome Intelligence",
}


async def decision_history(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
) -> DecisionHistoryResponse:
    """Reconstruct every major decision for a pursuit, in time order:
    deliverable generations, review transitions, human overrides, assumption
    judgments, and the recorded outcome — AI originals and human adjustments
    side by side."""
    entries: list[DecisionTimelineEntry] = []
    name_ids: set[uuid.UUID] = set()

    # Generations of decision deliverables.
    outputs = list(
        (
            await db.execute(
                select(AIOutput)
                .where(AIOutput.opportunity_id == opportunity_id)
                .where(AIOutput.module_id.in_(REVIEWABLE_MODULES))
                .order_by(AIOutput.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    for o in outputs:
        summary = decision_summary_for(o.module_id, o.output_json or {})
        entries.append(
            DecisionTimelineEntry(
                kind="generated",
                module_id=o.module_id,
                label=f"{_MODULE_LABELS.get(o.module_id, o.module_id)} generated",
                detail=f"MissionIQ recommendation: {summary}" if summary else None,
                occurred_at=o.created_at,
            )
        )

    # Review transitions across all cycles.
    reviews = list(
        (
            await db.execute(
                select(DeliverableReview).where(
                    DeliverableReview.opportunity_id == opportunity_id
                )
            )
        )
        .scalars()
        .all()
    )
    review_modules = {r.id: r.module_id for r in reviews}
    if reviews:
        events = list(
            (
                await db.execute(
                    select(ReviewEvent)
                    .where(ReviewEvent.review_id.in_(list(review_modules)))
                    .order_by(ReviewEvent.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        for e in events:
            module_id = review_modules.get(e.review_id)
            label = _MODULE_LABELS.get(module_id or "", module_id or "Deliverable")
            if e.actor_user_id:
                name_ids.add(e.actor_user_id)
            entries.append(
                DecisionTimelineEntry(
                    kind=f"review_{e.action}",  # type: ignore[arg-type]
                    module_id=module_id,
                    label=f"{label} {e.action}",
                    detail=e.decision_summary,
                    reason=e.notes,
                    actor_name=str(e.actor_user_id) if e.actor_user_id else None,
                    occurred_at=e.created_at,
                )
            )

    # Human overrides (decision ledger + feedback).
    overrides = list(
        (
            await db.execute(
                select(HumanOverride)
                .where(HumanOverride.opportunity_id == opportunity_id)
                .order_by(HumanOverride.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    for o in overrides:
        if o.created_by_user_id:
            name_ids.add(o.created_by_user_id)
        entries.append(
            DecisionTimelineEntry(
                kind="decision_overridden"
                if o.override_type == "decision"
                else "score_overridden",
                module_id=o.module_id,
                label=f"{_MODULE_LABELS.get(o.module_id, o.module_id)}: {o.field} overridden",
                original_value=(o.original_value or {}).get("value"),
                adjusted_value=(o.override_value or {}).get("value"),
                reason=o.reason,
                actor_name=str(o.created_by_user_id) if o.created_by_user_id else None,
                occurred_at=o.created_at,
            )
        )

    # Assumption judgments.
    validations = list(
        (
            await db.execute(
                select(AssumptionValidation)
                .where(AssumptionValidation.opportunity_id == opportunity_id)
                .order_by(AssumptionValidation.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    for v in validations:
        if v.validator_user_id:
            name_ids.add(v.validator_user_id)
        entries.append(
            DecisionTimelineEntry(
                kind=f"assumption_{v.status}",  # type: ignore[arg-type]
                module_id=v.module_id,
                label=f"Assumption {v.status}",
                detail=v.assumption_text,
                reason=v.notes,
                actor_name=str(v.validator_user_id) if v.validator_user_id else None,
                occurred_at=v.created_at,
            )
        )

    # Recorded outcome (the terminal decision).
    outcome = (
        await db.execute(
            select(PursuitOutcome).where(PursuitOutcome.opportunity_id == opportunity_id)
        )
    ).scalar_one_or_none()
    if outcome is not None:
        if outcome.recorded_by_user_id:
            name_ids.add(outcome.recorded_by_user_id)
        entries.append(
            DecisionTimelineEntry(
                kind="outcome_recorded",
                label=f"Outcome recorded: {outcome.outcome.replace('_', ' ').title()}",
                detail=outcome.debrief_notes,
                actor_name=str(outcome.recorded_by_user_id)
                if outcome.recorded_by_user_id
                else None,
                occurred_at=outcome.decided_at or outcome.created_at,
            )
        )

    # Resolve actor names (entries currently hold user-id strings).
    names = await _user_names(db, name_ids)
    str_names = {str(k): v for k, v in names.items()}
    for entry in entries:
        if entry.actor_name and entry.actor_name in str_names:
            entry.actor_name = str_names[entry.actor_name]

    entries.sort(key=lambda e: e.occurred_at)
    return DecisionHistoryResponse(opportunity_id=opportunity_id, entries=entries)
