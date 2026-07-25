# 0002 Use GitHub user events polling in v1

## Context

GitHub activity is the first collection target, but webhooks require a GitHub App and a public callback surface.

## Decision

Use `GET /users/{username}/events` with pagination capped to five pages per sync.

## Consequences

This is simple enough for v1 and avoids app registration. The tradeoff is incomplete history because GitHub limits this endpoint to recent public activity, so a future v2 should use a GitHub App and webhooks.

