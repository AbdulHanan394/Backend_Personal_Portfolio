# 0001 Use uv for Python dependency management

## Context

The backend needs reproducible dependency installation for local development, CI, and Docker builds.

## Decision

Use `uv` as the default installer and project dependency workflow, with plain `pip` remaining a viable fallback in constrained environments.

## Consequences

CI can install quickly while `pyproject.toml` remains the source of truth. The Dockerfile currently uses `pip` inside the image so it stays portable even when `uv` is unavailable.

