"""Local filesystem BlobStore. Layout: {root}/{workspace_id}/{document_id}/{filename}."""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    base = os.path.basename(name) or "file"
    return _SAFE_NAME.sub("_", base)[:200]


class LocalBlobStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, *, workspace_id: uuid.UUID, key: str) -> Path:
        ws = str(workspace_id)
        prefix = f"{ws}/"
        if not key.startswith(prefix):
            raise PermissionError("Blob key does not match workspace scope.")
        path = self.root / key
        resolved = path.resolve()
        if not str(resolved).startswith(str(self.root.resolve())):
            raise PermissionError("Blob key escapes storage root.")
        return resolved

    async def write(
        self,
        *,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        data: bytes,
        filename: str,
    ) -> str:
        safe = _safe_filename(filename)
        key = f"{workspace_id}/{document_id}/{safe}"
        path = self._resolve(workspace_id=workspace_id, key=key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def read(self, *, workspace_id: uuid.UUID, key: str) -> bytes:
        path = self._resolve(workspace_id=workspace_id, key=key)
        return path.read_bytes()

    async def delete(self, *, workspace_id: uuid.UUID, key: str) -> None:
        path = self._resolve(workspace_id=workspace_id, key=key)
        try:
            path.unlink()
        except FileNotFoundError:
            return
