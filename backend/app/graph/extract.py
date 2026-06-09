"""Pure fact extraction: module output → knowledge-graph facts.

These functions have NO database or ORM dependency so they are trivially
unit-testable. The service layer (:mod:`app.graph.service`) consumes a
``FactBundle`` and persists it idempotently.

Every fact is anchored to the opportunity node where it was observed (the
edge ``source``), which gives the graph its provenance and lets the memory
layer answer "what did we learn on similar pursuits?".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Cap how many items we ingest from any one list field, to keep the graph
# signal-dense rather than absorbing every bullet a model emits.
_MAX_PER_FIELD = 15
_MAX_NAME = 400
_MAX_KEY = 300

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def normalize_key(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — for entity dedup."""
    s = (name or "").lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s[:_MAX_KEY]


@dataclass
class EntitySpec:
    entity_type: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return normalize_key(self.name)


@dataclass
class EdgeSpec:
    relation: str
    source: EntitySpec
    target: EntitySpec
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FactBundle:
    entities: list[EntitySpec] = field(default_factory=list)
    edges: list[EdgeSpec] = field(default_factory=list)

    def extend(self, other: "FactBundle") -> None:
        self.entities.extend(other.entities)
        self.edges.extend(other.edges)


def _opp_entity(opp: dict[str, Any]) -> EntitySpec:
    return EntitySpec(
        entity_type="opportunity",
        name=(opp.get("name") or "Untitled opportunity")[:_MAX_NAME],
        attributes={
            "agency": opp.get("agency"),
            "naics_code": opp.get("naics_code"),
            "contract_vehicle": opp.get("contract_vehicle"),
            "capture_stage": opp.get("capture_stage"),
        },
    )


def _clean_list(values: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(values, list):
        return out
    for v in values:
        if isinstance(v, str):
            text = v.strip()
        elif isinstance(v, dict):
            # StrategicPoint-style objects: prefer statement/name/title.
            text = (
                v.get("statement")
                or v.get("name")
                or v.get("title")
                or v.get("area")
                or ""
            ).strip()
        else:
            text = ""
        if text:
            out.append(text[:_MAX_NAME])
        if len(out) >= _MAX_PER_FIELD:
            break
    return out


def extract_opportunity_base(opp: dict[str, Any]) -> FactBundle:
    """Facts derivable from the opportunity record alone (agency, vehicle,
    incumbent). Ingested under the synthetic module id ``opportunity``."""
    src = _opp_entity(opp)
    bundle = FactBundle(entities=[src])

    agency = (opp.get("agency") or "").strip()
    if agency:
        tgt = EntitySpec("agency", agency, {"sub_agency": opp.get("sub_agency")})
        bundle.entities.append(tgt)
        bundle.edges.append(EdgeSpec("opportunity_for_agency", src, tgt))

    vehicle = (opp.get("contract_vehicle") or "").strip()
    if vehicle:
        tgt = EntitySpec("contract_vehicle", vehicle)
        bundle.entities.append(tgt)
        bundle.edges.append(EdgeSpec("opportunity_uses_vehicle", src, tgt))

    incumbent = (opp.get("incumbent") or "").strip()
    if incumbent:
        tgt = EntitySpec("competitor", incumbent, {"is_incumbent": True})
        bundle.entities.append(tgt)
        bundle.edges.append(
            EdgeSpec("opportunity_has_incumbent", src, tgt, {"is_incumbent": True})
        )

    return bundle


def _edges(
    src: EntitySpec,
    relation: str,
    entity_type: str,
    names: list[str],
    edge_attrs: dict[str, Any] | None = None,
) -> FactBundle:
    b = FactBundle()
    for name in names:
        tgt = EntitySpec(entity_type, name)
        b.entities.append(tgt)
        b.edges.append(EdgeSpec(relation, src, tgt, dict(edge_attrs or {})))
    return b


def extract_facts(
    module_id: str, output: dict[str, Any], opp: dict[str, Any]
) -> FactBundle:
    """Extract a module's structured contributions to the graph.

    Unknown modules (or non-ok output) simply contribute nothing.
    """
    if not isinstance(output, dict):
        return FactBundle()
    src = _opp_entity(opp)
    b = FactBundle()

    if module_id == "capture.customer_dna":
        # Enrich the Agency node with the synthesized customer portrait.
        agency = (opp.get("agency") or "").strip()
        if agency:
            b.entities.append(
                EntitySpec(
                    "agency",
                    agency,
                    {
                        "mission": output.get("mission"),
                        "strategic_goals": output.get("strategic_goals"),
                        "success_metrics": output.get("success_metrics"),
                        "risk_priorities": output.get("risk_priorities"),
                    },
                )
            )
        b.extend(
            _edges(
                src,
                "opportunity_involves_technology",
                "technology",
                _clean_list(output.get("technology_priorities")),
            )
        )

    elif module_id == "capture.company_dna":
        b.extend(
            _edges(
                src,
                "company_has_capability",
                "capability",
                _clean_list(output.get("core_capabilities")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_has_discriminator",
                "discriminator",
                _clean_list(output.get("differentiators")),
            )
        )
        b.extend(
            _edges(
                src,
                "company_has_past_performance",
                "past_performance",
                _clean_list(output.get("past_performance")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_uses_vehicle",
                "contract_vehicle",
                _clean_list(output.get("contract_vehicles")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_involves_technology",
                "technology",
                _clean_list(output.get("technology_partners")),
            )
        )

    elif module_id == "capture.evaluation_criteria":
        b.extend(
            _edges(
                src,
                "opportunity_has_discriminator",
                "discriminator",
                _clean_list(output.get("potential_discriminators")),
            )
        )

    elif module_id == "capture.risk_register":
        for lane in ("capture_risks", "proposal_risks", "delivery_risks", "customer_risks"):
            items = output.get(lane) or []
            for item in items[:_MAX_PER_FIELD]:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                tgt = EntitySpec(
                    "risk",
                    title[:_MAX_NAME],
                    {
                        "lane": lane.replace("_risks", ""),
                        "severity": item.get("severity"),
                    },
                )
                b.entities.append(tgt)
                b.edges.append(
                    EdgeSpec(
                        "opportunity_has_risk",
                        src,
                        tgt,
                        {
                            "lane": lane.replace("_risks", ""),
                            "severity": item.get("severity"),
                        },
                    )
                )

    elif module_id == "capture.capability_match":
        b.extend(
            _edges(
                src,
                "opportunity_has_discriminator",
                "discriminator",
                _clean_list(output.get("suggested_discriminators")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_has_win_theme",
                "win_theme",
                _clean_list(output.get("reusable_win_themes")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_requires_capability",
                "capability",
                _clean_list(output.get("missing_capabilities")),
                {"gap": True},
            )
        )

    elif module_id == "capture.win_strategy":
        b.extend(
            _edges(
                src,
                "opportunity_has_win_theme",
                "win_theme",
                _clean_list(output.get("win_themes")),
            )
        )
        b.extend(
            _edges(
                src,
                "opportunity_has_discriminator",
                "discriminator",
                _clean_list(output.get("key_discriminators")),
            )
        )
        comp = output.get("competitive_assessment") or {}
        competitors = comp.get("competitors") if isinstance(comp, dict) else None
        for c in (competitors or [])[:_MAX_PER_FIELD]:
            if not isinstance(c, dict):
                continue
            name = (c.get("name") or "").strip()
            if not name:
                continue
            tgt = EntitySpec(
                "competitor", name[:_MAX_NAME], {"threat_level": c.get("threat_level")}
            )
            b.entities.append(tgt)
            b.edges.append(
                EdgeSpec(
                    "opportunity_has_competitor",
                    src,
                    tgt,
                    {"threat_level": c.get("threat_level")},
                )
            )

    return b
