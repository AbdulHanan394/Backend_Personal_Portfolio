"""Embedding client interface and sentence-transformers implementation."""

import asyncio
from functools import lru_cache
from typing import Protocol

from app.config.settings import get_settings


class EmbeddingsClient(Protocol):
    """Minimal embedding interface used by storage and retrieval services."""

    async def embed(self, text: str) -> list[float]:
        """Return one embedding vector for the provided text."""


class SentenceTransformersEmbeddingsClient:
    """Local sentence-transformers embedding implementation."""

    async def embed(self, text: str) -> list[float]:
        """Embed text with the configured local model."""

        model = await asyncio.to_thread(_load_model)
        vector = await asyncio.to_thread(model.encode, text)
        return [float(value) for value in vector.tolist()]


@lru_cache
def _load_model() -> object:
    """Load the embedding model once per process."""

    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)

