"""CSV exports (Compliance, Risk). Streams the file."""
from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import OppScope
from app.models import ComplianceRequirement, Risk
from app.services.audit_service import write_audit
from app.core.dependencies import CurrentUser

router = APIRouter()


def _csv_response(rows: list[list[str]], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/opportunities/{opportunity_id}/exports/compliance.csv")
async def export_compliance(
    scope: OppScope, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    ws, _, opportunity_id = scope
    rows = (
        await db.execute(
            select(ComplianceRequirement).where(
                ComplianceRequirement.opportunity_id == opportunity_id
            )
        )
    ).scalars().all()
    out = [
        ["Code", "Requirement", "Source Page", "Source Section", "Owner", "Status", "Notes"]
    ]
    for r in rows:
        out.append(
            [
                r.requirement_code or "",
                r.requirement_text or "",
                str(r.source_page or ""),
                r.source_section or "",
                r.owner or "",
                r.status,
                r.notes or "",
            ]
        )
    await write_audit(
        db,
        action="export.compliance_csv",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity",
        target_id=opportunity_id,
        meta={"rows": len(rows)},
    )
    return _csv_response(out, "compliance-matrix.csv")


@router.get("/opportunities/{opportunity_id}/exports/risks.csv")
async def export_risks(
    scope: OppScope, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    ws, _, opportunity_id = scope
    rows = (
        await db.execute(select(Risk).where(Risk.opportunity_id == opportunity_id))
    ).scalars().all()
    out = [
        [
            "Title",
            "Category",
            "Impact",
            "Likelihood",
            "Mitigation",
            "Owner",
            "Status",
            "Source Page",
        ]
    ]
    for r in rows:
        out.append(
            [
                r.title or "",
                r.category or "",
                r.impact or "",
                r.likelihood or "",
                r.mitigation or "",
                r.owner or "",
                r.status,
                str(r.source_page or ""),
            ]
        )
    await write_audit(
        db,
        action="export.risk_csv",
        workspace_id=ws.id,
        actor_user_id=user.id,
        target_type="opportunity",
        target_id=opportunity_id,
        meta={"rows": len(rows)},
    )
    return _csv_response(out, "risk-register.csv")
