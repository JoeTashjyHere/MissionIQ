"""Module registry exposes expected modules."""
from __future__ import annotations

from app.intelligence import get_registry


def test_registry_includes_opportunity_summary():
    reg = get_registry()
    cls = reg.get("capture.opportunity_summary")
    assert cls is not None
    assert cls.group == "capture"
    assert cls.version == "v1"
    assert "executive_summary" in cls.output_schema_summary


def test_registry_listing_is_stable():
    reg = get_registry()
    ids = [m.id for m in reg.all()]
    assert "capture.opportunity_summary" in ids
