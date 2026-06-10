"""Base class for all intelligence modules.

Each module declares its id, group, prompt id+version, output schema, retrieval
query, and result post-processing. The platform's ``run_module`` orchestrator
calls a uniform ``run()`` interface, so adding a new module is purely
declarative.

Customer DNA dependency
-----------------------

A module that consumes the Customer DNA Profile sets
``requires_customer_dna = True``. The orchestrator then loads the latest
DNA Profile for the opportunity from ``ai_output`` and passes it to the
prompt template as the ``customer_dna`` Jinja variable.

If ``requires_customer_dna`` is True and no DNA Profile exists yet for the
opportunity, the module short-circuits with ``status = "insufficient_context"``
and a clear ``recommended_actions`` payload pointing the user to the DNA
synthesis step. This is the platform's anti-generic-AI guarantee: downstream
modules cannot run without the customer synthesis upstream of them.

Company Profile consumption (seller-side intelligence)
------------------------------------------------------

A module that personalizes output to the company *pursuing* the work sets
``consumes_company_profile = True``. The orchestrator loads the workspace
Company Profile + capabilities, serializes them into the ``company_profile``
Jinja variable, and computes ``seller_incomplete`` (True when the profile is
essentially empty). Unlike Customer DNA, the Company Profile is **optional**:
modules still run without it, but their prompts are instructed to clearly
label seller-side assumptions as incomplete so a capture lead is never misled
into thinking a fit assessment was grounded in real company data.

``company_profile`` and ``seller_incomplete`` are ALWAYS passed to the
prompt renderer (``None`` / ``False`` when not consumed) so every template
can reference them uniformly under Jinja ``StrictUndefined``.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.rag import Evidence, RAGEngine
from app.llm.base import LLMResponse
from app.llm.prompt_library import PromptLibrary
from app.llm.router import LLMRouter
from app.models import AIOutput, Capability, CompanyProfile, Opportunity

CUSTOMER_DNA_MODULE_ID = "capture.customer_dna"


@dataclass(slots=True)
class RAGContext:
    workspace_id: uuid.UUID
    opportunity_id: uuid.UUID
    include_market_intel: bool = True
    top_k: int = 12


@dataclass(slots=True)
class ModuleResult:
    output: dict[str, Any]
    evidence: list[Evidence]
    market_evidence: list[Evidence]
    llm: LLMResponse
    status: str = "ok"
    structured_writes: list[Any] = field(default_factory=list)


class _NoopLLMResponse:
    """Synthetic LLMResponse for short-circuit refusals (no LLM call made)."""

    provider = "missioniq"
    model = "no-call"
    input_tokens = 0
    output_tokens = 0
    latency_ms = 0
    text = ""


def _short_circuit_dna_missing() -> dict[str, Any]:
    return {
        "executive_summary": (
            "MissionIQ requires a Customer DNA Profile before producing "
            "consultant-grade output for this module. Generate the Customer "
            "DNA Profile first, then re-run."
        ),
        "key_findings": [],
        "supporting_evidence": [],
        "recommended_actions": [
            "Open the Customer DNA Profile tab and click Generate.",
            "Once the DNA Profile is generated, regenerate this module to "
            "produce mission-aligned analysis.",
        ],
        "_missing_dependency": "customer_dna",
    }


class BaseIntelligenceModule:
    id: ClassVar[str]
    group: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str]
    version: ClassVar[str] = "v1"
    prompt_id: ClassVar[str]
    prompt_version: ClassVar[str] = "v1"
    output_model: ClassVar[type[BaseModel]] | None = None
    output_schema_summary: ClassVar[dict[str, str]] = {}
    retrieval_query: ClassVar[str] = ""
    retrieval_top_k: ClassVar[int] = 12
    minimum_evidence: ClassVar[int] = 2
    # If True, the orchestrator loads the most recent Customer DNA Profile
    # for the opportunity and passes it to the prompt as ``customer_dna``.
    # If no DNA Profile exists yet, the module short-circuits with
    # ``status = "insufficient_context"`` and a clear remediation message.
    requires_customer_dna: ClassVar[bool] = False
    # If True, the orchestrator loads the workspace Company Profile +
    # capabilities and passes them as ``company_profile`` (with a
    # ``seller_incomplete`` flag). The profile is OPTIONAL: the module still
    # runs without it, but its prompt should label seller-side assumptions
    # as incomplete.
    consumes_company_profile: ClassVar[bool] = False
    # If True, the orchestrator loads Pursuit Memory (similar opportunities,
    # prior risks / discriminators / win themes from the knowledge graph) and
    # passes a compact view as ``memory``. This is how the institutional
    # memory layer powers reports — recalled items should be cited as
    # "Historical Evidence" / "Pursuit Memory".
    consumes_memory: ClassVar[bool] = False

    def __init__(
        self,
        *,
        db: AsyncSession,
        rag: RAGEngine,
        llm_router: LLMRouter,
        prompts: PromptLibrary,
    ) -> None:
        self.db = db
        self.rag = rag
        self.llm_router = llm_router
        self.prompts = prompts

    async def _load_customer_dna(
        self, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Return the most recent successful Customer DNA Profile payload, or None."""
        stmt = (
            select(AIOutput)
            .where(AIOutput.workspace_id == workspace_id)
            .where(AIOutput.opportunity_id == opportunity_id)
            .where(AIOutput.module_id == CUSTOMER_DNA_MODULE_ID)
            .where(AIOutput.status == "ok")
            .order_by(desc(AIOutput.created_at))
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        return row.output_json if row else None

    async def _load_latest_output(
        self, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID, module_id: str
    ) -> dict[str, Any] | None:
        """Return the most recent successful output payload for any module."""
        stmt = (
            select(AIOutput)
            .where(AIOutput.workspace_id == workspace_id)
            .where(AIOutput.opportunity_id == opportunity_id)
            .where(AIOutput.module_id == module_id)
            .where(AIOutput.status == "ok")
            .order_by(desc(AIOutput.created_at))
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        return row.output_json if row else None

    async def _load_company_profile(
        self, *, workspace_id: uuid.UUID
    ) -> tuple[dict[str, Any] | None, bool]:
        """Serialize the workspace Company Profile + capabilities.

        Returns ``(profile_dict_or_None, seller_incomplete)``. ``seller_incomplete``
        is True when the profile carries no meaningful seller-side signal, which
        the prompts use to label fit assessments as assumption-based.
        """
        cp = (
            await self.db.execute(
                select(CompanyProfile).where(
                    CompanyProfile.workspace_id == workspace_id
                )
            )
        ).scalar_one_or_none()
        if cp is None:
            return None, True

        caps = list(
            (
                await self.db.execute(
                    select(Capability)
                    .where(Capability.workspace_id == workspace_id)
                    .order_by(Capability.name.asc())
                )
            )
            .scalars()
            .all()
        )
        profile = _safe_company_profile(cp, caps)
        return profile, _is_seller_incomplete(profile)

    async def _load_pursuit_memory(
        self, *, ctx: RAGContext
    ) -> dict[str, Any] | None:
        """Compact view of Pursuit Memory for prompt consumption.

        Returns recalled, institutional knowledge so a report can fold prior
        risks / discriminators / win themes in as Historical Evidence. Returns
        None when there is no usable history yet.
        """
        # Imported lazily to avoid an import cycle (memory_service → graph →
        # models, none of which should pull the intelligence base at import).
        from app.services import memory_service

        pm = await memory_service.build_pursuit_memory(
            self.db,
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
        )
        if not pm.has_history:
            return None

        def _hist(items: Any) -> list[dict[str, Any]]:
            out = []
            for i in items:
                if i.basis != "historical":
                    continue
                item: dict[str, Any] = {
                    "label": i.label,
                    "frequency": i.frequency,
                    "basis": i.basis,
                }
                # Outcome Intelligence: decided-pursuit track record (a
                # historical correlation) so reports can weight recalled
                # knowledge by what actually happened.
                if getattr(i, "track_record", None):
                    item["track_record"] = i.track_record
                out.append(item)
            return out

        compact = {
            "summary": pm.summary,
            "similar_count": len(pm.similar_opportunities),
            "similar_opportunities": [
                {"name": s.name, "agency": s.agency, "reasons": s.reasons}
                for s in pm.similar_opportunities
            ],
            "prior_risks": _hist(pm.prior_risks),
            "prior_discriminators": _hist(pm.prior_discriminators),
            "prior_win_themes": _hist(pm.prior_win_themes),
            "inferences": pm.inferences,
        }
        # If nothing historical surfaced, don't bother the prompt.
        if not any(
            compact[k]
            for k in ("prior_risks", "prior_discriminators", "prior_win_themes")
        ):
            return None
        return compact

    async def extra_context(
        self, *, ctx: RAGContext, customer_dna: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Hook for modules that need additional prompt variables.

        Default returns nothing. Modules like Capability Match override this to
        load prior outputs (e.g. the latest Evaluation Criteria) for synthesis.
        """
        return {}

    async def run(
        self,
        *,
        opportunity: Opportunity,
        ctx: RAGContext,
        model_override: str | None = None,
    ) -> ModuleResult:
        # 1. Customer DNA prerequisite check (for downstream modules)
        customer_dna: dict[str, Any] | None = None
        if self.requires_customer_dna:
            customer_dna = await self._load_customer_dna(
                workspace_id=ctx.workspace_id,
                opportunity_id=ctx.opportunity_id,
            )
            if customer_dna is None:
                return ModuleResult(
                    output=_short_circuit_dna_missing(),
                    evidence=[],
                    market_evidence=[],
                    llm=LLMResponse(
                        text="",
                        provider="missioniq",
                        model="no-call",
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=0,
                    ),
                    status="insufficient_context",
                )

        # 2. Retrieve grounded evidence
        evidence = await self.rag.retrieve(
            query=self.retrieval_query or self.description,
            workspace_id=ctx.workspace_id,
            opportunity_id=ctx.opportunity_id,
            top_k=ctx.top_k or self.retrieval_top_k,
        )
        market_evidence: list[Evidence] = []
        if ctx.include_market_intel:
            market_evidence = await self.rag.retrieve_market(
                query=self.retrieval_query or self.description,
                workspace_id=ctx.workspace_id,
                opportunity_id=ctx.opportunity_id,
                top_k=4,
            )

        status = "ok"
        if len(evidence) < self.minimum_evidence:
            status = "insufficient_context"

        # 3. Optionally load seller-side Company Profile (always pass the
        #    variables so every template can reference them uniformly).
        company_profile: dict[str, Any] | None = None
        seller_incomplete = False
        if self.consumes_company_profile:
            company_profile, seller_incomplete = await self._load_company_profile(
                workspace_id=ctx.workspace_id
            )

        # 4. Optionally load Pursuit Memory (institutional knowledge graph)
        memory: dict[str, Any] | None = None
        if self.consumes_memory:
            memory = await self._load_pursuit_memory(ctx=ctx)

        # 5. Module-specific extra context (e.g. prior Evaluation Criteria)
        extra = await self.extra_context(ctx=ctx, customer_dna=customer_dna)

        # 6. Render prompt with opportunity + evidence + (optional) DNA + seller
        prompts = self.prompts
        system, user, _ = prompts.render(
            self.prompt_id,
            self.prompt_version,
            opportunity=_safe_opp(opportunity),
            evidence=evidence,
            market_evidence=market_evidence,
            customer_dna=customer_dna,
            company_profile=company_profile,
            seller_incomplete=seller_incomplete,
            memory=memory,
            **extra,
        )

        # 6. LLM call
        llm = self.llm_router.chat_provider(model_override)
        llm_resp = await llm.generate_json(system=system, user=user)
        try:
            output = json.loads(llm_resp.text)
        except Exception:
            output = {"_error": "model returned non-JSON output", "_raw": llm_resp.text[:2000]}
            status = "error"

        if self.output_model is not None and status == "ok":
            try:
                self.output_model.model_validate(output)
            except Exception as exc:  # noqa: BLE001
                output["_validation_error"] = str(exc)
                status = "error"

        return ModuleResult(
            output=output,
            evidence=evidence,
            market_evidence=market_evidence,
            llm=llm_resp,
            status=status,
        )


def _safe_opp(opp: Opportunity) -> dict[str, Any]:
    return {
        "name": opp.name,
        "agency": opp.agency,
        "sub_agency": opp.sub_agency,
        "solicitation_number": opp.solicitation_number,
        "naics_code": opp.naics_code,
        "due_date": opp.due_date.isoformat() if opp.due_date else None,
        "estimated_value_cents": opp.estimated_value_cents,
        "incumbent": opp.incumbent,
        "notes": opp.notes,
        "capture_stage": opp.capture_stage,
        "contract_vehicle": opp.contract_vehicle,
    }


def _safe_company_profile(
    cp: CompanyProfile, caps: list[Capability]
) -> dict[str, Any]:
    return {
        "legal_name": cp.legal_name,
        "primary_naics": cp.primary_naics,
        "size_standard": cp.size_standard,
        "certifications": cp.certifications or [],
        "overview": cp.overview,
        "differentiators": cp.differentiators,
        "past_performance_summary": cp.past_performance_summary,
        "contract_vehicles": cp.contract_vehicles or [],
        "technology_partners": cp.technology_partners or [],
        "case_studies": cp.case_studies,
        "key_personnel": cp.key_personnel,
        "geographic_footprint": cp.geographic_footprint,
        "security_posture": cp.security_posture,
        "delivery_model": cp.delivery_model,
        "pricing_posture": cp.pricing_posture,
        "capabilities": [
            {
                "name": c.name,
                "category": c.category,
                "maturity": c.maturity,
                "description": c.description,
                "keywords": c.keywords or [],
            }
            for c in caps
        ],
    }


# A profile is "incomplete" for seller-side reasoning when it has neither a
# narrative overview/differentiators nor any catalogued capabilities to match
# against the opportunity.
_SELLER_SIGNAL_FIELDS = (
    "overview",
    "differentiators",
    "past_performance_summary",
    "case_studies",
    "delivery_model",
    "security_posture",
)


def _is_seller_incomplete(profile: dict[str, Any]) -> bool:
    has_narrative = any(
        (profile.get(f) or "").strip() for f in _SELLER_SIGNAL_FIELDS
    )
    has_caps = bool(profile.get("capabilities"))
    has_lists = bool(
        profile.get("certifications")
        or profile.get("contract_vehicles")
        or profile.get("technology_partners")
    )
    return not (has_narrative or has_caps or has_lists)
