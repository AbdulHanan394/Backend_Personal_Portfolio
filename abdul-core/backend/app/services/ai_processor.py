"""AI enrichment service for summaries and metadata."""

import copy
import json
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from app.ai.llm_client import GeminiLLMClient, LLMClient
from app.ai.prompts.extract_tags import CATEGORIES, ENRICHMENT_SYSTEM_PROMPT
from app.models.activity import Activity

logger = logging.getLogger(__name__)

# Cap on how many commits/files we serialize into the LLM prompt from a
# single push event's compare data. GitHub payloads for very active pushes
# can carry hundreds of entries here; sending all of them balloons prompt
# size/cost for little added benefit to the summary.
MAX_SERIALIZED_ITEMS = 20


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
            result = ActivityEnrichment.model_validate_json(raw)
            result.tags = result.tags[:5]
            result.technologies = result.technologies[:5]
            return result
        except (PydanticValidationError, ValueError):
            retry_prompt = f"""
You MUST return ONLY valid JSON.

Schema:

{{
    "summary": "...",
    "tags": ["..."],
    "technologies": ["..."],
    "category": "..."
}}

Rules:

- summary under 300 characters
- category must be one of:

{CATEGORIES}

- No markdown
- No explanation
- No code fences

Activity:

{user_prompt}

Your previous answer:

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
                result = ActivityEnrichment.model_validate_json(retry_raw)
                result.tags = result.tags[:5]
                result.technologies = result.technologies[:5]
                return result
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

    tags: list[str] = []

    repo = payload.get("repo", {}).get("name")

    if repo:
        tags.append(repo)

    if activity.type:
        tags.append(activity.type.lower())

    technologies: list[str] = []

    compare = payload.get("payload", {}).get("compare", {})

    for file in compare.get("files", []):

        filename = file.get("filename", "").lower()

        if filename.endswith(".py"):
            technologies.append("Python")

        elif filename.endswith(".js"):
            technologies.append("JavaScript")

        elif filename.endswith(".ts"):
            technologies.append("TypeScript")

        elif filename.endswith(".tsx"):
            technologies.append("React")

        elif filename.endswith(".go"):
            technologies.append("Go")

    return ActivityEnrichment(
        summary=summary,
        tags=list(dict.fromkeys(tags))[:5],
        technologies=list(dict.fromkeys(technologies))[:5],
        category="Other",
    )


def _safe_payload_dict(activity: Activity) -> dict[str, Any]:
    """Return activity.raw_payload as a dict, or {} if missing/non-dict.

    raw_payload can be None, a dict, or (for some sources) a plain string,
    so anything that needs to key into it should go through this first.
    """

    payload = activity.raw_payload

    return payload if isinstance(payload, dict) else {}


def _capped_payload_for_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of payload with large commit/file arrays truncated.

    GitHub payloads for very active pushes can carry hundreds of commits
    or changed files; sending all of them to the LLM balloons prompt size
    and cost for little benefit to the summary, so we cap them here while
    leaving everything else in the raw event untouched.
    """

    if not payload:
        return {}

    capped = copy.deepcopy(payload)

    compare = capped.get("payload", {}).get("compare")

    if isinstance(compare, dict):

        commits = compare.get("commits")
        if isinstance(commits, list) and len(commits) > MAX_SERIALIZED_ITEMS:
            omitted = len(commits) - MAX_SERIALIZED_ITEMS
            compare["commits"] = commits[:MAX_SERIALIZED_ITEMS]
            compare["commits_omitted"] = omitted

        files = compare.get("files")
        if isinstance(files, list) and len(files) > MAX_SERIALIZED_ITEMS:
            omitted = len(files) - MAX_SERIALIZED_ITEMS
            compare["files"] = files[:MAX_SERIALIZED_ITEMS]
            compare["files_omitted"] = omitted

    return capped


def _build_user_prompt(activity: Activity) -> str:
    """Build a rich prompt including the full (size-capped) raw payload,
    so the LLM can see repository, commits, changed files, branch, PR
    details, release notes, etc. instead of just the activity title.
    """

    payload = _safe_payload_dict(activity)
    source_slug = activity.source.slug if activity.source else "unknown"

    repo_name = ""
    if source_slug == "github":
        repo = payload.get("repo")
        if isinstance(repo, dict):
            repo_name = repo.get("name", "")

    prompt_payload = _capped_payload_for_prompt(payload)

    lines = [
        f"You are given a {source_slug} activity.",
        "",
        "Write:",
        "",
        "1. A concise professional summary (2-4 sentences)",
        "2. Up to 5 technologies",
        "3. Up to 5 tags",
        "4. One category",
        "",
        "Return ONLY valid JSON.",
        "",
        "Activity",
        "",
        "Title:",
        activity.title,
        "",
        "Type:",
        activity.type,
    ]

    if repo_name:
        lines += ["", "Repository:", repo_name]

    lines += [
        "",
        "URL:",
        str(activity.url or ""),
        "",
        "Occurred:",
        str(activity.occurred_at),
        "",
        f"Raw {source_slug.title()} Event:",
        "",
        json.dumps(prompt_payload, indent=2, default=str),
    ]

    return "\n".join(lines)