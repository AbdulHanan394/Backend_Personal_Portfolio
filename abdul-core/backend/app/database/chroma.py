"""ChromaDB persistent collection factory."""

from functools import lru_cache
from typing import Any

from app.config.settings import get_settings


@lru_cache
def get_chroma_collection() -> Any:
    """Return the configured Chroma collection, creating it if needed."""

    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(settings.chroma_collection_name)

