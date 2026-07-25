"""AI enrichment service for summaries and metadata."""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from app.ai.llm_client import GeminiLLMClient, LLMClient
from app.ai.prompts.extract_tags import CATEGORIES, ENRICHMENT_SYSTEM_PROMPT
from app.models.activity import Activity

logger = logging.getLogger(__name__)


class ActivityEnrichment(BaseModel):
    """Validated structured output from the LLM."""

    summary: str = Field(min_length=1, max_length=400)
    tags: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    category: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        """Validate the category is one of the configured values."""

        if value not in CATEGORIES:
            raise ValueError(f"Invalid category from LLM: {value}")
        return value


class AIProcessor:
    """Run structured AI enrichment for activities."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or GeminiLLMClient()

    async def enrich(self, activity: Activity) -> ActivityEnrichment:
        """Return summary, tags, technologies, and category for an activity.

        Never raises. If the LLM call fails (quota, network, timeout) or
        returns invalid JSON twice in a row, falls back to a deterministic,
        rule-based enrichment built from the activity's raw payload.
        """

        user_prompt = _build_user_prompt(activity)

        try:
            raw = await self.llm_client.complete(
                ENRICHMENT_SYSTEM_PROMPT,
                user_prompt,
                json_output=True,
            )
        except Exception as exc:
            # Covers network errors, timeouts, and quota/rate-limit errors
            # (e.g. Gemini 429 RESOURCE_EXHAUSTED) raised by the LLM client.
            logger.warning(
                "LLM call failed for activity %s, using fallback enrichment: %s",
                getattr(activity, "id", None),
                exc,
            )
            return _build_fallback_enrichment(activity)

        try:
            return ActivityEnrichment.model_validate_json(raw)
        except (PydanticValidationError, ValueError):
            retry_prompt = f"""Your previous response was invalid.

Return ONLY a valid JSON object.

Do not wrap it in markdown.

Do not use ```.

Do not write explanations.

Return exactly:

{{
    "summary": "...",
    "tags": ["..."],
    "technologies": ["..."],
    "category": "..."
}}

Original Task:

{user_prompt}

Previous Response:

{raw}
"""
            try:
                retry_raw = await self.llm_client.complete(
                    ENRICHMENT_SYSTEM_PROMPT,
                    retry_prompt,
                    json_output=True,
                )
            except Exception as exc:
                logger.warning(
                    "LLM retry call failed for activity %s, using fallback enrichment: %s",
                    getattr(activity, "id", None),
                    exc,
                )
                return _build_fallback_enrichment(activity)

            try:
                return ActivityEnrichment.model_validate_json(retry_raw)
            except (PydanticValidationError, ValueError) as exc:
                # Two consecutive invalid-JSON responses likely means a
                # schema/prompt regression rather than a transient outage.
                # Log at error level so it's distinguishable from the
                # quota/network fallback above, but still degrade gracefully
                # rather than raising, so the activity still gets a summary.
                logger.error(
                    "AI enrichment JSON parsing failed twice for activity %s: %s",
                    getattr(activity, "id", None),
                    retry_raw,
                    exc_info=exc,
                )
                return _build_fallback_enrichment(activity)


def _build_fallback_enrichment(activity: Activity) -> ActivityEnrichment:
    """Deterministic, rule-based enrichment used when the LLM is unavailable
    or fails to return valid structured output."""

    payload = activity.raw_payload or {}
    summary = activity.title

    if activity.type == "Push":
        compare = payload.get("payload", {}).get("compare", {})
        commits = compare.get("commits", [])
        files = compare.get("files", [])
        repo = payload.get("repo", {}).get("name", "")

        parts = []

        if repo:
            parts.append(f"Updated repository {repo}.")

        if commits:
            parts.append(
                "Commits: "
                + ", ".join(c.get("message", "") for c in commits[:3])
                + "."
            )

        if files:
            parts.append(
                "Files changed: "
                + ", ".join(f.get("filename", "") for f in files[:5])
                + "."
            )

        summary = " ".join(parts) or summary

    elif activity.type == "Create":
        ref = payload.get("payload", {}).get("ref")
        description = payload.get("payload", {}).get("description")

        summary = f"Created branch '{ref}'."

        if description:
            summary += f" Repository description: {description}"

    return ActivityEnrichment(
        summary=summary,
        tags=[],
        technologies=[],
        category="Other",
    )


def _build_user_prompt(activity: Activity) -> str:
    """Build the LLM user prompt from an activity."""

    payload: dict[str, Any] = {
        "title": activity.title,
        "description": getattr(activity, "description", None),
        "type": activity.type,
        "source": activity.source.slug if activity.source else None,
        "raw_payload": activity.raw_payload,
    }
    return json.dumps(payload, default=str)