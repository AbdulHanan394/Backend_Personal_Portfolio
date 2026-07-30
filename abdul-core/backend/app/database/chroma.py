"""ChromaDB persistent collection factory."""

from functools import lru_cache
from typing import Any

from app.config.settings import get_settings


@lru_cache
def get_chroma_collection():
    import chromadb

    settings = get_settings()

    print("=" * 60)
    print("CHROMA PATH:", settings.chroma_persist_dir)
    print("FILES:", __import__("os").listdir(settings.chroma_persist_dir))
    print("=" * 60)

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir
    )

    collection = client.get_or_create_collection(
        settings.chroma_collection_name
    )

    print("COLLECTION COUNT:", collection.count())

    return collection
