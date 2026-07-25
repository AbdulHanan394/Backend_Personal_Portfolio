# 0005 Use embedded persistent ChromaDB

## Context

Vector retrieval is required, but v1 is a single backend service and does not need a separate vector server.

## Decision

Use ChromaDB's persistent local client with a mounted volume.

## Consequences

Local development has fewer moving parts. If the API scales to multiple replicas, Chroma should move to a shared hosted/server deployment.

