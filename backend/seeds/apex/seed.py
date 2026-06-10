"""Apex Federal Solutions — comprehensive MissionIQ showcase environment.

Run: python -m seeds.apex.seed
     python -m seeds.seed --apex
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import session_scope
from app.core.security import hash_password
from app.models import (
    Capability,
    CompanyProfile,
    Opportunity,
    TeamMember,
    User,
    Workspace,
)
from app.models.opportunity import CAPTURE_STAGES
from app.services.outcome_intelligence_service import OUTCOME_TO_STAGE
from seeds.apex.constants import (
    CAPABILITIES,
    COMPANY_PROFILE,
    DEMO_PASSWORD,
    DEMO_USERS,
    HISTORICAL_OUTCOMES,
    INTELLIGENCE_MODULES,
    PROPOSAL_ASSETS,
    SHOWCASE_PURSUITS,
    WORKSPACE_NAME,
    WORKSPACE_SLUG,
    capture_stage_for_pursuit,
)
from seeds.apex.helpers import (
    ensure_proposal_document,
    record_pursuit_outcome,
    seed_connectors,
    seed_governance_activity,
    seed_graph_extras,
    seed_intelligence_for_pursuit,
    seed_proposal_assets,
)


async def load_apex_workspace(*, if_empty: bool = False) -> dict[str, str]:
    """Idempotent loader for the Apex Federal showcase. Returns login hints."""
    async with session_scope() as db:
        marker = (
            await db.execute(
                select(Workspace).where(Workspace.slug == WORKSPACE_SLUG)
            )
        ).scalar_one_or_none()
        if marker and if_empty:
            print(f"[apex] Workspace '{WORKSPACE_SLUG}' already exists; skipping.")
            return _login_info(str(marker.id))

        users: dict[str, User] = {}
        for spec in DEMO_USERS:
            row = (
                await db.execute(select(User).where(User.email == spec["email"]))
            ).scalar_one_or_none()
            if row is None:
                row = User(
                    email=spec["email"],
                    password_hash=hash_password(DEMO_PASSWORD),
                    full_name=spec["full_name"],
                    is_active=True,
                )
                db.add(row)
                await db.flush()
                print(f"[apex] Created user: {spec['email']}")
            users[spec["email"]] = row

        admin = users["sarah.mitchell@apexfederal.demo"]
        ws = marker
        if ws is None:
            ws = Workspace(
                name=WORKSPACE_NAME,
                slug=WORKSPACE_SLUG,
                description=(
                    "Apex Federal Solutions showcase — synthetic federal growth "
                    "organization with institutional knowledge."
                ),
                owner_user_id=admin.id,
                settings_json={"demo": True, "showcase": True},
            )
            db.add(ws)
            await db.flush()
            print(f"[apex] Created workspace: {WORKSPACE_SLUG}")

        for spec in DEMO_USERS:
            member = (
                await db.execute(
                    select(TeamMember)
                    .where(TeamMember.workspace_id == ws.id)
                    .where(TeamMember.user_id == users[spec["email"]].id)
                )
            ).scalar_one_or_none()
            if member is None:
                db.add(
                    TeamMember(
                        workspace_id=ws.id,
                        user_id=users[spec["email"]].id,
                        role=spec["role"],
                        joined_at=datetime.now(UTC) - timedelta(days=400),
                    )
                )

        cp = (
            await db.execute(
                select(CompanyProfile).where(CompanyProfile.workspace_id == ws.id)
            )
        ).scalar_one_or_none()
        if cp is None:
            cp = CompanyProfile(workspace_id=ws.id, **COMPANY_PROFILE)
            db.add(cp)
            await db.flush()
            for cap in CAPABILITIES:
                db.add(Capability(workspace_id=ws.id, company_profile_id=cp.id, **cap))
            print("[apex] Populated company profile and capabilities")

        opportunity_map: dict[str, uuid.UUID] = {}
        flagship_id: uuid.UUID | None = None

        for ps in SHOWCASE_PURSUITS:
            stage = capture_stage_for_pursuit(
                outcome=ps.outcome, active_stage=ps.capture_stage
            )
            opp = (
                await db.execute(
                    select(Opportunity)
                    .where(Opportunity.workspace_id == ws.id)
                    .where(Opportunity.solicitation_number == ps.solicitation_number)
                )
            ).scalar_one_or_none()
            if opp is None:
                opp = Opportunity(
                    workspace_id=ws.id,
                    name=ps.name,
                    agency=ps.agency,
                    sub_agency=ps.sub_agency,
                    contract_vehicle=ps.contract_vehicle,
                    solicitation_number=ps.solicitation_number,
                    naics_code="541512",
                    due_date=datetime.now(UTC) + timedelta(days=45 if ps.outcome is None else -30),
                    posted_date=datetime.now(UTC) - timedelta(days=120),
                    estimated_value_cents=ps.value_cents,
                    capture_stage=stage,
                    incumbent=ps.incumbent,
                    notes=ps.loss_reason or ps.no_bid_reason or f"Showcase pursuit: {ps.name}",
                    created_by_user_id=admin.id,
                )
                db.add(opp)
                await db.flush()
                print(f"[apex] Created pursuit: {ps.name}")
            elif opp.capture_stage not in CAPTURE_STAGES:
                opp.capture_stage = (
                    OUTCOME_TO_STAGE[ps.outcome] if ps.outcome else stage
                )
                db.add(opp)
            opportunity_map[ps.solicitation_number] = opp.id
            if ps.flagship:
                flagship_id = opp.id

            base = datetime.now(UTC) - timedelta(days=60 if ps.outcome else 10)
            await seed_intelligence_for_pursuit(
                db,
                workspace_id=ws.id,
                opportunity=opp,
                user_id=admin.id,
                modules=INTELLIGENCE_MODULES,
                include_outcome_intel=ps.outcome is not None,
                base_time=base,
            )

            if ps.outcome:
                await record_pursuit_outcome(
                    db,
                    opportunity=opp,
                    outcome=ps.outcome,
                    user_id=admin.id,
                    value_cents=ps.value_cents if ps.outcome == "won" else None,
                    factors=["transition approach", "past performance"]
                    if ps.outcome == "won"
                    else ["incumbent advantage"]
                    if ps.outcome == "lost"
                    else ["capability gap"],
                    debrief=ps.loss_reason or ps.no_bid_reason,
                    competitor=ps.incumbent if ps.outcome == "lost" else None,
                )

            if ps.flagship:
                outputs = {}
                from seeds.apex.helpers import upsert_ai_output

                for mid in INTELLIGENCE_MODULES:
                    outputs[mid] = await upsert_ai_output(
                        db,
                        workspace_id=ws.id,
                        opportunity=opp,
                        module_id=mid,
                        user_id=admin.id,
                    )
                await seed_governance_activity(
                    db,
                    workspace_id=ws.id,
                    opportunity_id=opp.id,
                    outputs=outputs,
                    users=users,
                )

        # Historical pursuits for outcome intelligence depth (38 additional).
        for i, outcome in enumerate(HISTORICAL_OUTCOMES, start=1):
            sol = f"APEX-HIST-{i:04d}"
            stage = capture_stage_for_pursuit(outcome=outcome)
            opp = (
                await db.execute(
                    select(Opportunity)
                    .where(Opportunity.workspace_id == ws.id)
                    .where(Opportunity.solicitation_number == sol)
                )
            ).scalar_one_or_none()
            if opp is None:
                agencies = [
                    "Centers for Medicare Programs",
                    "Veteran Benefits Administration",
                    "Federal Citizen Services Agency",
                    "National Energy Operations Agency",
                    "Department of Mission Security",
                ]
                opp = Opportunity(
                    workspace_id=ws.id,
                    name=f"Historical Pursuit {i:04d}",
                    agency=agencies[i % len(agencies)],
                    solicitation_number=sol,
                    estimated_value_cents=25_000_000_00 + i * 1_000_000_00,
                    capture_stage=stage,
                    created_by_user_id=admin.id,
                    posted_date=datetime.now(UTC) - timedelta(days=400 + i),
                )
                db.add(opp)
                await db.flush()
            elif opp.capture_stage not in CAPTURE_STAGES:
                opp.capture_stage = OUTCOME_TO_STAGE.get(outcome, stage)
                db.add(opp)
            await record_pursuit_outcome(
                db,
                opportunity=opp,
                outcome=outcome,
                user_id=admin.id,
                value_cents=opp.estimated_value_cents if outcome == "won" else None,
            )

        doc = await ensure_proposal_document(
            db,
            workspace_id=ws.id,
            opportunity_id=flagship_id or next(iter(opportunity_map.values())),
            user_id=admin.id,
            filename="apex_proposal_volume_cx_modernization.txt",
        )
        await seed_proposal_assets(
            db,
            workspace_id=ws.id,
            assets=PROPOSAL_ASSETS,
            doc=doc,
            opportunity_map=opportunity_map,
            user_id=admin.id,
        )
        print(f"[apex] Seeded {len(PROPOSAL_ASSETS)} proposal intelligence assets")

        await seed_connectors(
            db,
            workspace_id=ws.id,
            user_id=admin.id,
            opportunity_id=flagship_id,
        )
        await seed_graph_extras(db, workspace_id=ws.id)
        print("[apex] Connectors, automation history, and graph extras ready")

        ws_id = str(ws.id)

    print("[apex] Done.")
    return _login_info(ws_id)


def _login_info(workspace_id: str = "") -> dict[str, str]:
    return {
        "workspace": WORKSPACE_SLUG,
        "workspace_id": workspace_id,
        "email": "sarah.mitchell@apexfederal.demo",
        "password": DEMO_PASSWORD,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Apex Federal demo workspace")
    parser.add_argument("--if-empty", action="store_true", help="Skip if workspace exists")
    args = parser.parse_args()
    try:
        info = asyncio.run(load_apex_workspace(if_empty=args.if_empty))
        print(
            f"\nLogin: {info['email']} / {info['password']}\n"
            f"Workspace slug: {info['workspace']}\n"
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
