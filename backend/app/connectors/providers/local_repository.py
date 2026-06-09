"""Local Repository connector — Phase 1, fully functional.

Ingests pursuit documents from a directory on the MissionIQ host. Layout:

    <root_path>/
      <Pursuit Name A>/         ← one subdirectory per pursuit
        rfp.pdf
        sections_l_m.docx
      <Pursuit Name B>/
        pws.txt

Each subdirectory becomes (or matches) a MissionIQ pursuit; its files are
ingested through the existing document pipeline with connector provenance.
This makes the end-to-end automation (sync → pursuit → ingestion → Customer
DNA → … → Executive Brief) fully demonstrable offline with real documents.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from app.connectors.base import (
    BaseConnectorProvider,
    ConnectorHealth,
    DiscoveryResult,
    ExternalDocument,
    ExternalOpportunity,
)
from app.core.errors import AppError

_ALLOWED_SUFFIXES = {".pdf": "application/pdf", ".docx": (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
), ".txt": "text/plain", ".md": "text/plain"}


def _slug(value: str) -> str:
    return "-".join("".join(c if c.isalnum() else " " for c in value.lower()).split())


class LocalRepositoryProvider(BaseConnectorProvider):
    provider_id: ClassVar[str] = "local_repository"
    label: ClassVar[str] = "Local Repository"
    description: ClassVar[str] = (
        "Document repository connector for a directory on the MissionIQ host. "
        "Each subdirectory becomes a pursuit; its PDF/DOCX/TXT files are "
        "ingested through the document pipeline with connector provenance. "
        "Fully functional — no external service required."
    )
    connector_type: ClassVar[str] = "document_repository"
    auth_mode: ClassVar[str] = "none"
    phase: ClassVar[int] = 1
    provides_opportunities: ClassVar[bool] = True
    provides_documents: ClassVar[bool] = True
    config_fields: ClassVar[list[dict[str, Any]]] = [
        {
            "key": "root_path",
            "label": "Root directory",
            "placeholder": "/data/pursuits",
            "required": True,
        },
    ]

    def _root(self, config: dict[str, Any]) -> Path:
        raw = (config.get("root_path") or "").strip()
        if not raw:
            raise AppError(
                "Local Repository requires a root_path in its configuration.",
                status_code=422,
                code="connector.local_repository.misconfigured",
            )
        return Path(raw).expanduser().resolve()

    async def test_connection(
        self, *, config: dict[str, Any], secret: str | None
    ) -> ConnectorHealth:
        try:
            root = self._root(config)
        except AppError as exc:
            return ConnectorHealth(ok=False, message=exc.detail)
        if not root.is_dir():
            return ConnectorHealth(
                ok=False, message=f"Directory does not exist: {root}"
            )
        return ConnectorHealth(ok=True, message=f"Repository readable: {root}")

    async def discover(
        self,
        *,
        config: dict[str, Any],
        secret: str | None,
        since: datetime | None = None,
    ) -> DiscoveryResult:
        root = self._root(config)
        if not root.is_dir():
            raise AppError(
                f"Local Repository directory does not exist: {root}",
                status_code=422,
                code="connector.local_repository.missing_root",
            )
        opportunities: list[ExternalOpportunity] = []
        for sub in sorted(p for p in root.iterdir() if p.is_dir()):
            attachments: list[ExternalDocument] = []
            opp_ext_id = f"localrepo:{_slug(sub.name)}"
            for f in sorted(p for p in sub.iterdir() if p.is_file()):
                mime = _ALLOWED_SUFFIXES.get(f.suffix.lower())
                if mime is None:
                    continue
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
                if since is not None and mtime <= since:
                    continue
                attachments.append(
                    ExternalDocument(
                        external_id=f"{opp_ext_id}:{_slug(f.name)}",
                        filename=f.name,
                        mime_type=mime,
                        doc_type="other",
                        fetch_ref=str(f),
                        opportunity_external_id=opp_ext_id,
                    )
                )
            opportunities.append(
                ExternalOpportunity(
                    external_id=opp_ext_id,
                    name=sub.name,
                    notes="Created from the Local Repository connector.",
                    attachments=attachments,
                )
            )
        return DiscoveryResult(opportunities=opportunities)

    async def fetch_document(
        self, *, config: dict[str, Any], secret: str | None, ref: ExternalDocument
    ) -> bytes:
        root = self._root(config)
        path = Path(ref.fetch_ref).resolve()
        # Containment check: never read outside the configured repository.
        if not path.is_relative_to(root):
            raise AppError(
                "Document reference escapes the configured repository root.",
                status_code=400,
                code="connector.local_repository.path_escape",
            )
        return path.read_bytes()
