# 0006 Build deployment images to GHCR

## Context

The hosting target is not specified, but CI/CD needs a concrete artifact.

## Decision

Build and push Docker images to GitHub Container Registry on `main`.

## Consequences

The deployment workflow has a stable image artifact. The final deploy step remains a documented TODO until VPS or PaaS hosting is chosen.

