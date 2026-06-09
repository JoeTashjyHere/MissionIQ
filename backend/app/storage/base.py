"""BlobStore protocol. Implementations: LocalBlobStore, (future) S3BlobStore."""
from __future__ import annotations

import uuid
from typing import Protocol

from app.core.config import get_settings


class BlobStore(Protocol):
    """Workspace-scoped, content-addressed blob storage."""

    async def write(
        self,
        *,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        data: bytes,
        filename: str,
    ) -> str:
        """Persist bytes and return an opaque storage key."""

    async def read(self, *, workspace_id: uuid.UUID, key: str) -> bytes:
        """Read bytes. Raises FileNotFoundError if absent."""

    async def delete(self, *, workspace_id: uuid.UUID, key: str) -> None:
        """Best-effort delete; idempotent."""


def get_blob_store() -> BlobStore:
    """Return the configured BlobStore."""
    from app.storage.local import LocalBlobStore

    settings = get_settings()
    if settings.blob_store == "local":
        return LocalBlobStore(root=settings.blob_local_root)
    if settings.blob_store == "s3":  # pragma: no cover - future
        raise NotImplementedError(
            "S3 BlobStore implementation is not yet enabled. See storage/s3.py."
        )
    raise ValueError(f"Unsupported MIQ_BLOB_STORE: {settings.blob_store}")
