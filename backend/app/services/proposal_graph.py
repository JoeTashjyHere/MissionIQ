"""Proposal asset → Knowledge Graph mapping.

Pure functions that turn extracted assets into FactBundles for idempotent
ingestion via ``app.graph.service``.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.graph.extract import EntitySpec, EdgeSpec, FactBundle, normalize_key
from app.models.proposal_asset import ASSET_TYPES

_EXTRACTION_MODULE = "repository.proposal_extraction"

_ASSET_TO_ENTITY = {
    "executive_summary": "executive_summary",
    "staffing_approach": "staffing_narrative",
    "management_approach": "staffing_narrative",
    "transition_approach": "transition_narrative",
    "risk_mitigation": "risk_mitigation",
    "win_theme": "win_theme",
    "discriminator": "discriminator",
    "past_performance": "past_performance",
}


def graph_entity_type(asset_type: str) -> str:
    if asset_type not in ASSET_TYPES:
        return "proposal_asset"
    return _ASSET_TO_ENTITY.get(asset_type, "proposal_asset")


def build_graph_bundle(
    *,
    asset_title: str,
    asset_type: str,
    agency: str | None,
    opportunity: dict[str, Any] | None,
    capabilities: list[str] | None = None,
    win_themes: list[str] | None = None,
) -> FactBundle:
    """Build graph facts for one extracted proposal asset."""
    bundle = FactBundle()
    entity_type = graph_entity_type(asset_type)
    asset_ent = EntitySpec(
        entity_type=entity_type,
        name=asset_title[:400],
        attributes={"asset_type": asset_type},
    )
    bundle.entities.append(asset_ent)

    if agency:
        agency_ent = EntitySpec(entity_type="agency", name=agency[:400])
        bundle.entities.append(agency_ent)
        bundle.edges.append(
            EdgeSpec(
                relation="agency_uses_proposal_asset",
                source=agency_ent,
                target=asset_ent,
            )
        )

    if opportunity:
        opp_ent = EntitySpec(
            entity_type="opportunity",
            name=(opportunity.get("name") or "Untitled")[:400],
            attributes={
                "agency": opportunity.get("agency"),
                "capture_stage": opportunity.get("capture_stage"),
            },
        )
        bundle.entities.append(opp_ent)
        bundle.edges.append(
            EdgeSpec(
                relation="proposal_asset_from_opportunity",
                source=asset_ent,
                target=opp_ent,
            )
        )
        bundle.edges.append(
            EdgeSpec(
                relation="opportunity_used_asset",
                source=opp_ent,
                target=asset_ent,
            )
        )

    for cap in (capabilities or [])[:8]:
        cap_ent = EntitySpec(entity_type="capability", name=cap[:400])
        bundle.entities.append(cap_ent)
        bundle.edges.append(
            EdgeSpec(
                relation="proposal_asset_linked_capability",
                source=asset_ent,
                target=cap_ent,
            )
        )

    for theme in (win_themes or [])[:8]:
        if normalize_key(theme) == normalize_key(asset_title):
            continue
        theme_ent = EntitySpec(entity_type="win_theme", name=theme[:400])
        bundle.entities.append(theme_ent)
        bundle.edges.append(
            EdgeSpec(
                relation="proposal_asset_supports_win_theme",
                source=asset_ent,
                target=theme_ent,
            )
        )

    return bundle


def extraction_module_id() -> str:
    return _EXTRACTION_MODULE
