"""Idempotent seed script. Run with: python -m seeds.seed --if-empty"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.db import session_scope
from app.core.security import hash_password
from app.ingestion import process_document
from app.models import (
    Capability,
    CompanyProfile,
    Document,
    Opportunity,
    TeamMember,
    User,
    Workspace,
)
from app.storage import get_blob_store

DEMO_EMAIL = "demo@missioniq.dev"
DEMO_PASSWORD = "MissionIQ!Demo2026"
DEMO_WORKSPACE = "Demo Workspace"

ROOT = Path(__file__).resolve().parent
EXAMPLE_DOC = ROOT / "example_documents" / "example_rfp.txt"


async def seed(if_empty: bool) -> None:
    async with session_scope() as db:
        existing = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
        if existing and if_empty:
            print(f"[seed] Demo user '{DEMO_EMAIL}' already exists; skipping.")
            return
        if existing:
            user = existing
            print(f"[seed] Demo user '{DEMO_EMAIL}' already exists; will continue.")
        else:
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Demo Analyst",
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"[seed] Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        ws = (
            await db.execute(select(Workspace).where(Workspace.slug == "demo"))
        ).scalar_one_or_none()
        if ws is None:
            ws = Workspace(
                name=DEMO_WORKSPACE,
                slug="demo",
                description="Demo workspace seeded by MissionIQ.",
                owner_user_id=user.id,
                settings_json={},
            )
            db.add(ws)
            await db.flush()
            db.add(
                TeamMember(
                    workspace_id=ws.id,
                    user_id=user.id,
                    role="administrator",
                    joined_at=datetime.now(UTC),
                )
            )
            cp = CompanyProfile(
                workspace_id=ws.id,
                legal_name="Demo Federal Solutions LLC",
                primary_naics="541512",
                size_standard="Small Business",
                certifications=["8(a)", "SDVOSB"],
                overview=(
                    "Demo Federal Solutions LLC is a small business systems integrator "
                    "specializing in mission operations, cybersecurity, and analytics "
                    "for the Department of Defense and Department of Veterans Affairs."
                ),
                differentiators=(
                    "FedRAMP-aligned managed services, 24x7 SOC, embedded data engineering, "
                    "and a CMMI-3 process maturity."
                ),
                past_performance_summary="DHA, VA, US Army C5ISR, DLA — five active prime contracts.",
                contract_vehicles=["8(a) Sole Source", "GSA MAS", "CIO-SP3 SB"],
                technology_partners=["AWS", "Microsoft", "Splunk", "Databricks"],
                case_studies=(
                    "Stood up a 24x7 mission operations center for a DoD health system in 45 days "
                    "with zero mission downtime during transition. Delivered a FedRAMP Moderate "
                    "ATO for a VA analytics platform in under nine months."
                ),
                key_personnel=(
                    "Program Manager (PMP, 15 yrs DHA/MHS), Information System Security Officer "
                    "(CISSP), Lead Data Engineer (former DHA contractor), Transition Lead (ITIL)."
                ),
                geographic_footprint=(
                    "National delivery; cleared staff concentrated in the National Capital Region "
                    "and San Antonio. Remote-eligible for non-sensitive work."
                ),
                security_posture=(
                    "FedRAMP Moderate experience, IL5 lineage, facility clearance, and a track "
                    "record of clean A&A / continuous ATO support."
                ),
                delivery_model=(
                    "Embedded agile delivery pods backed by a shared 24x7 SOC and a centralized "
                    "engineering bench. CMMI-3 processes with measured SLAs."
                ),
                pricing_posture=(
                    "Competitive value positioning enabled by lean indirect rates and a "
                    "blended on/near-site staffing model."
                ),
            )
            db.add(cp)
            await db.flush()
            db.add_all(
                [
                    Capability(
                        workspace_id=ws.id,
                        company_profile_id=cp.id,
                        name="Mission Operations Center Support",
                        category="Operations",
                        maturity="mature",
                        description="24x7 ops center staffing, incident response, COOP exercises.",
                        keywords=["mission ops", "soc", "24x7", "coop"],
                    ),
                    Capability(
                        workspace_id=ws.id,
                        company_profile_id=cp.id,
                        name="FedRAMP Moderate Engineering",
                        category="Cyber",
                        maturity="mature",
                        description="ATO support, control implementation, continuous monitoring.",
                        keywords=["fedramp", "ato", "nist 800-53", "moderate"],
                    ),
                    Capability(
                        workspace_id=ws.id,
                        company_profile_id=cp.id,
                        name="Performance Analytics Dashboards",
                        category="Data",
                        maturity="developing",
                        description="Power BI / Tableau dashboards over operational telemetry.",
                        keywords=["dashboards", "power bi", "tableau"],
                    ),
                ]
            )
            print(f"[seed] Created demo workspace: {ws.slug}")
        else:
            print(f"[seed] Demo workspace '{ws.slug}' already exists.")

        opp = (
            await db.execute(
                select(Opportunity)
                .where(Opportunity.workspace_id == ws.id)
                .where(Opportunity.solicitation_number == "W912DY-26-R-9999")
            )
        ).scalar_one_or_none()
        if opp is None:
            opp = Opportunity(
                workspace_id=ws.id,
                name="DHA Mission Operations Support Services",
                agency="Defense Health Agency",
                sub_agency="Operations Center",
                contract_vehicle="8(a) Sole Source",
                solicitation_number="W912DY-26-R-9999",
                naics_code="541512",
                psc_code="D399",
                set_aside="8(a)",
                due_date=datetime.now(UTC) + timedelta(days=60),
                posted_date=datetime.now(UTC) - timedelta(days=20),
                estimated_value_cents=48_500_000_00,
                capture_stage="capture",
                incumbent="Acme Federal Services LLC",
                notes="Hot opportunity. Strong incumbent. Differentiation on FedRAMP and analytics.",
                created_by_user_id=user.id,
            )
            db.add(opp)
            await db.flush()
            print(f"[seed] Created example opportunity: {opp.name}")
        else:
            print(f"[seed] Example opportunity already exists: {opp.name}")

        existing_doc = (
            await db.execute(
                select(Document)
                .where(Document.opportunity_id == opp.id)
                .where(Document.name == "example_rfp.txt")
            )
        ).scalar_one_or_none()
        if existing_doc is None and EXAMPLE_DOC.exists():
            data = EXAMPLE_DOC.read_bytes()
            doc_id = uuid.uuid4()
            blob = get_blob_store()
            key = await blob.write(
                workspace_id=ws.id,
                document_id=doc_id,
                data=data,
                filename="example_rfp.txt",
            )
            import hashlib

            doc = Document(
                id=doc_id,
                workspace_id=ws.id,
                opportunity_id=opp.id,
                name="example_rfp.txt",
                doc_type="rfp",
                mime_type="text/plain",
                size_bytes=len(data),
                blob_key=key,
                sha256=hashlib.sha256(data).hexdigest(),
                status="uploaded",
                uploaded_by_user_id=user.id,
                uploaded_at=datetime.now(UTC),
            )
            db.add(doc)
            await db.flush()
            print(f"[seed] Uploaded example RFP, running ingestion pipeline...")
            await process_document(db=db, document_id=doc.id)
            print(f"[seed] Ingested example RFP (status={doc.status}).")
        elif existing_doc:
            print(f"[seed] Example document already present.")
        else:
            print(f"[seed] Example document file missing at {EXAMPLE_DOC}; skipping.")

    print("[seed] Done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Skip seeding when a demo user already exists.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(seed(if_empty=args.if_empty))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
