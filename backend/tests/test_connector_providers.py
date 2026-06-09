"""Phase 1 connector provider contracts.

The Salesforce and SharePoint mocks must be deterministic (the local_stub
philosophy) so the whole sync → pursuit → automation pipeline is demoable and
testable offline. The Local Repository provider is fully real and is tested
against a temporary directory, mirroring test_storage.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.connectors.providers.local_repository import LocalRepositoryProvider
from app.connectors.providers.salesforce import SalesforceProvider
from app.connectors.providers.sharepoint import SharePointProvider
from app.core.errors import AppError

# ── Salesforce (mock CRM) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_salesforce_discovery_is_deterministic_and_normalized():
    provider = SalesforceProvider()
    first = await provider.discover(config={}, secret="token")
    second = await provider.discover(config={}, secret="token")
    assert [o.external_id for o in first.opportunities] == [
        o.external_id for o in second.opportunities
    ]
    assert len(first.opportunities) >= 1
    for opp in first.opportunities:
        assert opp.external_id and opp.name and opp.agency
        # Every mock pursuit carries capture material for downstream DNA runs.
        assert opp.attachments, opp.external_id
        for doc in opp.attachments:
            assert doc.opportunity_external_id == opp.external_id
            assert doc.doc_type == "capture_notes"


@pytest.mark.asyncio
async def test_salesforce_mock_data_is_clearly_marked():
    provider = SalesforceProvider()
    result = await provider.discover(config={}, secret="token")
    for opp in result.opportunities:
        assert "mock" in (opp.notes or "").lower()


@pytest.mark.asyncio
async def test_salesforce_connection_requires_credential():
    provider = SalesforceProvider()
    missing = await provider.test_connection(config={}, secret=None)
    assert missing.ok is False
    present = await provider.test_connection(config={}, secret="token")
    assert present.ok is True


@pytest.mark.asyncio
async def test_salesforce_fetch_document_returns_text_bytes():
    provider = SalesforceProvider()
    result = await provider.discover(config={}, secret="token")
    doc = result.opportunities[0].attachments[0]
    data = await provider.fetch_document(config={}, secret="token", ref=doc)
    assert isinstance(data, bytes) and len(data) > 100
    assert b"CAPTURE NOTES" in data


# ── SharePoint (mock document repository) ───────────────────────────────────


@pytest.mark.asyncio
async def test_sharepoint_discovers_documents_with_folder_hints():
    provider = SharePointProvider()
    result = await provider.discover(config={}, secret="token")
    assert result.opportunities == []
    assert len(result.documents) >= 1
    for doc in result.documents:
        # Pursuit resolution relies on the folder name hint.
        assert doc.opportunity_name_hint
        data = await provider.fetch_document(config={}, secret="token", ref=doc)
        assert isinstance(data, bytes) and data


# ── Local Repository (real) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_local_repository_discovers_pursuit_directories(tmp_path: Path):
    pursuit = tmp_path / "DHA Mission Ops Recompete"
    pursuit.mkdir()
    (pursuit / "rfp.txt").write_text("RFP body text")
    (pursuit / "notes.md").write_text("capture notes")
    (pursuit / "skip.xlsx").write_bytes(b"binary")  # unsupported suffix
    (tmp_path / "loose-file.txt").write_text("not in a pursuit dir")

    provider = LocalRepositoryProvider()
    result = await provider.discover(
        config={"root_path": str(tmp_path)}, secret=None
    )
    assert len(result.opportunities) == 1
    opp = result.opportunities[0]
    assert opp.name == "DHA Mission Ops Recompete"
    names = {d.filename for d in opp.attachments}
    assert names == {"rfp.txt", "notes.md"}

    data = await provider.fetch_document(
        config={"root_path": str(tmp_path)}, secret=None, ref=opp.attachments[0]
    )
    assert data in (b"RFP body text", b"capture notes")


@pytest.mark.asyncio
async def test_local_repository_blocks_path_escape(tmp_path: Path):
    from app.connectors.base import ExternalDocument

    inside = tmp_path / "repo"
    inside.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("should never be readable")

    provider = LocalRepositoryProvider()
    with pytest.raises(AppError) as exc:
        await provider.fetch_document(
            config={"root_path": str(inside)},
            secret=None,
            ref=ExternalDocument(
                external_id="x", filename="secret.txt", fetch_ref=str(outside)
            ),
        )
    assert exc.value.code == "connector.local_repository.path_escape"


@pytest.mark.asyncio
async def test_local_repository_requires_root_path():
    provider = LocalRepositoryProvider()
    health = await provider.test_connection(config={}, secret=None)
    assert health.ok is False
    missing = await provider.test_connection(
        config={"root_path": "/definitely/not/a/real/dir"}, secret=None
    )
    assert missing.ok is False


@pytest.mark.asyncio
async def test_local_repository_incremental_since_filter(tmp_path: Path):
    from datetime import UTC, datetime, timedelta

    pursuit = tmp_path / "Pursuit"
    pursuit.mkdir()
    (pursuit / "old.txt").write_text("old")

    provider = LocalRepositoryProvider()
    future = datetime.now(UTC) + timedelta(hours=1)
    result = await provider.discover(
        config={"root_path": str(tmp_path)}, secret=None, since=future
    )
    # Pursuit directory still discovered, but unchanged files are excluded.
    assert len(result.opportunities) == 1
    assert result.opportunities[0].attachments == []
