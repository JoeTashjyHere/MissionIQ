"""S3-backed BlobStore (deferred implementation; interface-compatible)."""
from __future__ import annotations

import uuid


class S3BlobStore:
    """Placeholder. Implement using aiobotocore / boto3 with SSE-KMS in Milestone 5.

    The contract is identical to LocalBlobStore so callers do not change when we
    flip MIQ_BLOB_STORE=s3.
    """

    def __init__(self, *, bucket: str, region: str, prefix: str) -> None:  # pragma: no cover
        self.bucket = bucket
        self.region = region
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""

    async def write(
        self,
        *,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        data: bytes,
        filename: str,
    ) -> str:  # pragma: no cover
        raise NotImplementedError

    async def read(self, *, workspace_id: uuid.UUID, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    async def delete(self, *, workspace_id: uuid.UUID, key: str) -> None:  # pragma: no cover
        raise NotImplementedError
