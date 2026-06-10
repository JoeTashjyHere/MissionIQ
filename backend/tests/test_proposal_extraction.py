"""Proposal asset extraction — prompt contract and stub schema."""
from __future__ import annotations

import json

from app.llm.prompt_library import get_prompt_library
from app.llm.providers.local_stub import LocalStubLLM, _build_skeleton
from app.schemas.proposal_repository import ProposalExtractionOutput


async def test_extract_assets_prompt_renders():
    lib = get_prompt_library()
    system, user, _ = lib.render(
        "proposal.extract_assets",
        "v1",
        document={"name": "CMS Proposal Vol 1", "doc_type": "proposal", "page_count": 42, "chunk_count": 10},
        opportunity={"name": "CMS Ops", "agency": "CMS", "customer": "CMS"},
        evidence=[],
    )
    assert "proposal" in system.lower()
    assert "never" in system.lower() or "do not" in system.lower()
    assert "CMS Proposal" in user


async def test_extract_stub_validates_schema():
    user = 'RETURN JSON WITH THIS SCHEMA\n"assets":\n"asset_type"\n"document_summary"'
    skeleton = _build_skeleton(user)
    payload = {"__stub__": True, **skeleton}
    out = ProposalExtractionOutput.model_validate(payload)
    assert len(out.assets) >= 1
    assert out.assets[0].asset_type in ("transition_approach", "win_theme")


async def test_extract_stub_via_llm():
    llm = LocalStubLLM()
    resp = await llm.generate_json(
        system="extract",
        user='RETURN JSON WITH THIS SCHEMA\n"assets":\n"asset_type"\n"document_summary"',
    )
    data = json.loads(resp.text)
    ProposalExtractionOutput.model_validate(data)
