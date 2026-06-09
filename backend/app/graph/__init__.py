"""MissionIQ Knowledge Graph — institutional memory layer.

This package turns per-opportunity intelligence into reusable, cross-pursuit
institutional knowledge. Pure fact extraction lives in :mod:`extract`; the
persistence + query layer lives in :mod:`service`.
"""
from app.graph.extract import (
    EdgeSpec,
    EntitySpec,
    FactBundle,
    extract_facts,
    extract_opportunity_base,
    normalize_key,
)

__all__ = [
    "EdgeSpec",
    "EntitySpec",
    "FactBundle",
    "extract_facts",
    "extract_opportunity_base",
    "normalize_key",
]
