# 0003 Use local MiniLM embeddings

## Context

Semantic search needs low-cost vectors and predictable local behavior during early development.

## Decision

Use `sentence-transformers/all-MiniLM-L6-v2` behind an embedding client interface.

## Consequences

Embeddings are free and 384-dimensional, keeping Chroma storage small. The service can later swap to an API embedding provider without changing callers.

