"""Storage abstraction."""
from app.storage.base import BlobStore, get_blob_store

__all__ = ["BlobStore", "get_blob_store"]
