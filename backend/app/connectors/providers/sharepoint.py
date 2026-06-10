"""SharePoint connector — Phase 1, mock document-repository provider.

Discovers documents organized in libraries/folders. Documents resolve to a
pursuit via ``opportunity_name_hint`` (the folder name) — the sync engine
matches it against existing opportunity names and skips unmatched documents
(counted in job stats) rather than guessing.

A real implementation replaces ``discover``/``fetch_document`` with Microsoft
Graph calls; shapes and sync behavior are unchanged.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from app.connectors.base import (
    BaseConnectorProvider,
    ConnectorHealth,
    DiscoveryResult,
    ExternalDocument,
)

_MOCK_FILES: list[dict[str, str]] = [
    {
        "external_id": "SP-DOC-1001",
        "filename": "DHA_Mission_Ops_Sections_L_M.txt",
        "folder": "DHA Enterprise Mission Operations Support",
        "doc_type": "sections_l_m",
        "body": (
            "SECTION L — INSTRUCTIONS TO OFFERORS (mock SharePoint document)\n"
            "Volumes: Technical, Past Performance, Price. Page limits apply.\n\n"
            "SECTION M — EVALUATION FACTORS\n"
            "Factor 1: Technical/Management Approach (most important).\n"
            "Factor 2: Past Performance relevance and recency.\n"
            "Factor 3: Transition Approach.\n"
            "Factors 1–3, when combined, are significantly more important than price.\n"
        ),
    },
    {
        "external_id": "SP-DOC-1002",
        "filename": "DHA_Mission_Ops_PWS_excerpt.txt",
        "folder": "DHA Enterprise Mission Operations Support",
        "doc_type": "pws",
        "body": (
            "PERFORMANCE WORK STATEMENT (excerpt — mock SharePoint document)\n"
            "The Contractor shall provide 24x7 mission operations center support, "
            "including monitoring, incident management, and reporting. The "
            "Contractor shall complete transition-in within 60 days with no "
            "degradation of mission services. Security operations shall align to "
            "the agency zero-trust roadmap.\n"
        ),
    },
]


class SharePointProvider(BaseConnectorProvider):
    provider_id: ClassVar[str] = "sharepoint"
    label: ClassVar[str] = "SharePoint"
    description: ClassVar[str] = (
        "Document repository connector. Discovers pursuit documents from "
        "SharePoint libraries (folder name → pursuit) and ingests them through "
        "the MissionIQ document pipeline. Currently backed by a deterministic "
        "mock provider."
    )
    connector_type: ClassVar[str] = "document_repository"
    auth_mode: ClassVar[str] = "api_key"
    phase: ClassVar[int] = 1
    provides_opportunities: ClassVar[bool] = False
    provides_documents: ClassVar[bool] = True
    provides_proposal_archives: ClassVar[bool] = True
    config_fields: ClassVar[list[dict[str, Any]]] = [
        {
            "key": "site_url",
            "label": "Site URL",
            "placeholder": "https://yourorg.sharepoint.com/sites/capture",
            "required": False,
        },
        {
            "key": "library",
            "label": "Document library",
            "placeholder": "Pursuit Documents",
            "required": False,
        },
    ]

    async def test_connection(
        self, *, config: dict[str, Any], secret: str | None
    ) -> ConnectorHealth:
        if not secret:
            return ConnectorHealth(
                ok=False,
                message="No credential set. Add an access token to connect SharePoint.",
            )
        return ConnectorHealth(
            ok=True,
            message="Mock SharePoint site reachable. (Deterministic mock provider.)",
        )

    async def discover(
        self,
        *,
        config: dict[str, Any],
        secret: str | None,
        since: datetime | None = None,
    ) -> DiscoveryResult:
        documents = [
            ExternalDocument(
                external_id=f["external_id"],
                filename=f["filename"],
                mime_type="text/plain",
                doc_type=f["doc_type"],
                fetch_ref=f["external_id"],
                opportunity_name_hint=f["folder"],
            )
            for f in _MOCK_FILES
        ]
        return DiscoveryResult(documents=documents)

    async def fetch_document(
        self, *, config: dict[str, Any], secret: str | None, ref: ExternalDocument
    ) -> bytes:
        f = next(
            (x for x in _MOCK_FILES if x["external_id"] == ref.fetch_ref),
            _MOCK_FILES[0],
        )
        return f["body"].encode("utf-8")
