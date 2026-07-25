# 0004 Use Anthropic for structured enrichment

## Context

Activity enrichment requires compact summaries and reliable JSON metadata extraction.

## Decision

Use the official Anthropic SDK behind a provider-agnostic `complete()` interface.

## Consequences

The AI processor does not depend on Anthropic types. If model availability changes, only configuration or the client implementation needs to move.

