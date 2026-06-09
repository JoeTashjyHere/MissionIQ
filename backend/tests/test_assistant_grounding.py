"""Intelligence Assistant grounding contract — local stub side.

The full chat endpoint behavior is exercised by docker-compose integration
runs (it touches Postgres + pgvector). Here we lock the offline-stub contract
that powers the demo without API keys: with no evidence, the assistant must
refuse with ``insufficient_context``; with evidence, it must return ``ok``
plus citations referencing the evidence ids.
"""
from __future__ import annotations

import json

import pytest

from app.llm.providers.local_stub import LocalStubLLM


ASSISTANT_SYSTEM = (
    "Answer the user's QUESTION using ONLY the EVIDENCE blocks provided. "
    "If insufficient, return status=insufficient_context."
)


def _make_user_prompt(question: str, evidence: list[dict]) -> str:
    if evidence:
        evidence_block = "\n\n".join(
            f'[E{i + 1}] (opportunity_document) document="{e["doc"]}" page={e["page"]}\n{e["snippet"]}'
            for i, e in enumerate(evidence)
        )
    else:
        evidence_block = "(no opportunity_document evidence available)"
    return (
        f"QUESTION:\n{question}\n\n"
        f"OPPORTUNITY EVIDENCE:\n{evidence_block}\n\n"
        f"MARKET INTELLIGENCE:\n(none linked)\n"
    )


@pytest.mark.asyncio
async def test_stub_refuses_when_no_evidence():
    stub = LocalStubLLM()
    user = _make_user_prompt(
        "What are the major requirements?", evidence=[]
    )
    resp = await stub.generate_json(system=ASSISTANT_SYSTEM, user=user)
    payload = json.loads(resp.text)

    assert payload["status"] == "insufficient_context"
    assert "upload" in payload["answer"].lower()
    assert payload["citations"] == []
    assert isinstance(payload["follow_ups"], list)


@pytest.mark.asyncio
async def test_stub_responds_with_citations_when_evidence_present():
    stub = LocalStubLLM()
    user = _make_user_prompt(
        "What are the major requirements?",
        evidence=[
            {
                "doc": "example_rfp.txt",
                "page": 1,
                "snippet": (
                    "The Contractor shall provide 24x7 operational support "
                    "of the DHA mission operations center."
                ),
            },
            {
                "doc": "example_rfp.txt",
                "page": 2,
                "snippet": "Evaluation factors in descending order of importance.",
            },
        ],
    )
    resp = await stub.generate_json(system=ASSISTANT_SYSTEM, user=user)
    payload = json.loads(resp.text)

    assert payload["status"] == "ok"
    assert payload["answer"]
    assert payload["citations"], "must cite at least one evidence ref"
    for c in payload["citations"]:
        assert c["evidence_ref"].startswith("E") or c["evidence_ref"].startswith("M")


@pytest.mark.asyncio
async def test_stub_assistant_distinguishes_unknown_prompt():
    stub = LocalStubLLM()
    resp = await stub.generate_json(
        system="generic system",
        user="Please describe the weather today in plain text.",
    )
    payload = json.loads(resp.text)
    assert payload.get("_unknown_prompt") is True
