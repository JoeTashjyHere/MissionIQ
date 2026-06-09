"""Customer DNA Profile module — schema, prompt contract, and stub rendering.

These tests lock the contract that the platform's central synthesis step
honors:

- The DNA module is registered.
- Its v1 prompt renders cleanly with and without evidence.
- The local_stub LLM produces output that validates against
  ``CustomerDnaProfile`` in both "with evidence" and "without evidence"
  branches.
- The module is correctly marked as NOT requiring DNA itself (it produces
  the DNA).
"""
from __future__ import annotations

import json

import pytest

from app.intelligence import get_registry
from app.intelligence.modules.capture.customer_dna import CustomerDnaModule
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import CustomerDnaProfile


class _FakeEvidence:
    def __init__(
        self,
        chunk_id: str,
        document_name: str,
        page_start: int,
        section_path: str | None,
        snippet: str,
    ) -> None:
        self.chunk_id = chunk_id
        self.document_name = document_name
        self.page_start = page_start
        self.page_end = page_start
        self.section_path = section_path
        self.snippet = snippet
        self.market_record_id = None
        self.document_id = "doc-1"
        self.score = 0.9


_OPP = {
    "name": "DHA Mission Operations Support",
    "agency": "Defense Health Agency",
    "sub_agency": None,
    "solicitation_number": "W912DY-26-R-9999",
    "naics_code": "541512",
    "due_date": None,
    "estimated_value_cents": 48_500_000_00,
    "incumbent": "Acme Federal Services LLC",
    "notes": None,
    "capture_stage": "qualification",
    "contract_vehicle": "GSA OASIS+",
}


def _render(evidence: list[_FakeEvidence]) -> tuple[str, str]:
    prompts = get_prompt_library()
    system, user, _ = prompts.render(
        CustomerDnaModule.prompt_id,
        CustomerDnaModule.prompt_version,
        opportunity=_OPP,
        evidence=evidence,
        market_evidence=[],
        customer_dna=None,
    )
    return system, user


def test_module_registered_and_does_not_require_dna():
    registry = get_registry()
    cls = registry.get("capture.customer_dna")
    assert cls is CustomerDnaModule
    assert cls.requires_customer_dna is False  # this module IS the producer


def test_module_metadata_advertises_eight_attributes():
    schema = CustomerDnaModule.output_schema_summary
    for required in (
        "mission",
        "strategic_goals",
        "core_values",
        "success_metrics",
        "operational_challenges",
        "technology_priorities",
        "risk_priorities",
        "stakeholder_concerns",
    ):
        assert required in schema, f"missing {required} in output_schema_summary"


def test_prompt_renders_with_and_without_evidence():
    system, user_empty = _render([])
    assert "senior federal capture strategist" in system
    assert "Customer DNA Profile" in system
    assert "(no document evidence available)" in user_empty
    # Schema markers expected in the user prompt body
    assert "strategic_goals" in user_empty
    assert "stakeholder_concerns" in user_empty
    assert "core_values" in user_empty
    assert "operational_challenges" in user_empty
    assert "confidence" in user_empty

    ev = [
        _FakeEvidence(
            chunk_id="c1",
            document_name="example_rfp.txt",
            page_start=1,
            section_path="Section L.3.1",
            snippet="The Contractor shall provide 24x7 operational support.",
        )
    ]
    _, user_with = _render(ev)
    assert "[E1]" in user_with
    assert "example_rfp.txt" in user_with


@pytest.mark.asyncio
async def test_stub_output_validates_when_evidence_present():
    ev = [
        _FakeEvidence(
            chunk_id="c1",
            document_name="example_rfp.txt",
            page_start=1,
            section_path="Section C.4",
            snippet="The agency requires continuity-of-operations for mission systems.",
        ),
        _FakeEvidence(
            chunk_id="c2",
            document_name="example_rfp.txt",
            page_start=2,
            section_path="Section M.2",
            snippet="Evaluation factors in descending order of importance.",
        ),
    ]
    system, user = _render(ev)
    stub = LocalStubLLM()
    resp = await stub.generate_json(system=system, user=user)
    payload = json.loads(resp.text)

    parsed = CustomerDnaProfile.model_validate(payload)
    assert parsed.mission
    assert parsed.strategic_goals
    assert parsed.core_values
    assert parsed.success_metrics
    assert parsed.operational_challenges
    assert parsed.technology_priorities
    assert parsed.risk_priorities
    assert parsed.stakeholder_concerns
    assert parsed.executive_summary
    assert parsed.confidence in {"high", "medium", "low", "insufficient"}


@pytest.mark.asyncio
async def test_stub_returns_insufficient_when_no_evidence():
    system, user = _render([])
    stub = LocalStubLLM()
    resp = await stub.generate_json(system=system, user=user)
    payload = json.loads(resp.text)

    parsed = CustomerDnaProfile.model_validate(payload)
    assert parsed.confidence == "insufficient"
    assert parsed.strategic_goals == []
    assert parsed.stakeholder_concerns == []
    assert parsed.recommended_actions
    # Must tell the user what to upload to make the synthesis possible.
    assert any("upload" in a.lower() for a in parsed.recommended_actions)
