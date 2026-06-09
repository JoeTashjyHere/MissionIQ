"""LocalBlobStore enforces workspace prefix and round-trips bytes."""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest

from app.storage.local import LocalBlobStore


@pytest.mark.asyncio
async def test_local_blob_store_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalBlobStore(root=str(Path(tmp) / "blobs"))
        ws = uuid.uuid4()
        doc = uuid.uuid4()
        key = await store.write(workspace_id=ws, document_id=doc, data=b"hello", filename="x.txt")
        assert key.startswith(f"{ws}/")
        assert await store.read(workspace_id=ws, key=key) == b"hello"
        await store.delete(workspace_id=ws, key=key)
        # Subsequent reads raise
        import pytest as _pt

        with _pt.raises(FileNotFoundError):
            await store.read(workspace_id=ws, key=key)


@pytest.mark.asyncio
async def test_local_blob_store_rejects_cross_workspace_key():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalBlobStore(root=str(Path(tmp) / "blobs"))
        ws_a = uuid.uuid4()
        ws_b = uuid.uuid4()
        key = await store.write(
            workspace_id=ws_a, document_id=uuid.uuid4(), data=b"hello", filename="x.txt"
        )
        with pytest.raises(PermissionError):
            await store.read(workspace_id=ws_b, key=key)
