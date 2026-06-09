"""Opportunity Summary module — schema, prompt contract, and stub rendering.

These tests exercise the module end-to-end at the boundaries that don't
require Postgres: the prompt library can render the v1 prompt, the local_stub
LLM produces output that validates against ``OpportunitySummaryOutput``, and
the prompt advertises every field the Pydantic schema requires.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.intelligence.modules.capture.opportunity_summary import (
    OpportunitySummaryModule,
)
from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM
from app.schemas.intelligence import (
    OpportunitySummaryOutput,
    SupportingEvidenceItem,
)


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


class _FakeOpp:
    name = "DHA Mission Operations Support"
    agency = "Defense Health Agency"
    solicitation_number = "W912DY-26-R-9999"
    naics_code = "541512"
    due_date = None
    estimated_value_cents = 48_500_000_00
    incumbent = "Acme Federal Services LLC"
    notes = None


def _render_prompt(evidence: list[_FakeEvidence]) -> tuple[str, str]:
    prompts = get_prompt_library()
    system, user, _ = prompts.render(
        OpportunitySummaryModule.prompt_id,
        OpportunitySummaryModule.prompt_version,
        opportunity={
            "name": _FakeOpp.name,
            "agency": _FakeOpp.agency,
            "solicitation_number": _FakeOpp.solicitation_number,
            "naics_code": _FakeOpp.naics_code,
            "due_date": None,
            "estimated_value_cents": _FakeOpp.estimated_value_cents,
            "incumbent": _FakeOpp.incumbent,
            "notes": None,
        },
        evidence=evidence,
        market_evidence=[],
    )
    return system, user


def test_module_metadata_advertises_four_canonical_sections():
    schema = OpportunitySummaryModule.output_schema_summary
    for required in (
        "executive_summary",
        "key_findings",
        "supporting_evidence",
        "recommended_actions",
    ):
        assert required in schema, f"missing {required} in output_schema_summary"


def test_prompt_renders_with_and_without_evidence():
    system, user_empty = _render_prompt([])
    assert "Operational Intelligence Analyst" in system
    assert "(no document evidence available)" in user_empty
    assert "executive_summary" in user_empty
    assert "key_findings" in user_empty
    assert "supporting_evidence" in user_empty
    assert "recommended_actions" in user_empty

    ev = [
        _FakeEvidence(
            chunk_id="c1",
            document_name="example_rfp.txt",
            page_start=1,
            section_path="Section L.3.1",
            snippet=(
                "The Contractor shall describe its approach to providing 24x7 "
                "operational support of the DHA mission operations center."
            ),
        )
    ]
    _, user_with = _render_prompt(ev)
    assert "[E1]" in user_with
    assert "example_rfp.txt" in user_with
    assert "Section L.3.1" in user_with


@pytest.mark.asyncio
async def test_stub_output_validates_against_schema_when_evidence_present():
    ev = [
        _FakeEvidence(
            chunk_id="c1",
            document_name="example_rfp.txt",
            page_start=2,
            section_path="Section M.2",
            snippet="Evaluation factors in descending order of importance.",
        ),
        _FakeEvidence(
            chunk_id="c2",
            document_name="example_rfp.txt",
            page_start=3,
            section_path="Section C.4",
            snippet="CDRL A001 — Monthly Status Report (due 10th of each month).",
        ),
    ]
    system, user = _render_prompt(ev)
    stub = LocalStubLLM()
    resp = await stub.generate_json(system=system, user=user)
    payload = json.loads(resp.text)

    parsed = OpportunitySummaryOutput.model_validate(payload)
    assert parsed.executive_summary
    assert parsed.key_findings, "stub should produce findings when evidence present"
    assert all(isinstance(f, str) for f in parsed.key_findings)
    assert parsed.supporting_evidence, "stub should emit supporting_evidence refs"
    for item in parsed.supporting_evidence:
        assert isinstance(item, SupportingEvidenceItem)
        assert item.evidence_ref.startswith(("E", "M"))
    assert parsed.recommended_actions


@pytest.mark.asyncio
async def test_stub_returns_insufficient_context_without_evidence():
    system, user = _render_prompt([])
    stub = LocalStubLLM()
    resp = await stub.generate_json(system=system, user=user)
    payload = json.loads(resp.text)

    parsed = OpportunitySummaryOutput.model_validate(payload)
    assert "Insufficient context" in parsed.executive_summary
    assert parsed.key_findings == []
    assert parsed.supporting_evidence == []
    assert parsed.recommended_actions
    assert any("upload" in a.lower() for a in parsed.recommended_actions)


def test_supporting_evidence_item_rejects_garbage():
    with pytest.raises(ValidationError):
        SupportingEvidenceItem.model_validate({"finding": "missing ref"})
