"""Append to the audit log. Best-effort; never blocks the primary action."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog

logger = get_logger(__name__)


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    workspace_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    try:
        db.add(
            AuditLog(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                meta=meta or {},
                ip=ip,
                user_agent=user_agent,
            )
        )
    except Exception:  # noqa: BLE001 - never blow up callers
        logger.exception("audit.write_failed", action=action)
