"""Normalize source payloads into a common activity shape."""

from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel

from app.middleware.error_handler import ValidationError


class NormalizedActivity(BaseModel):
    """Common activity shape before persistence."""

    source_slug: str
    external_id: str
    type: str
    title: str
    url: str
    occurred_at: datetime
    raw_payload: dict[str, Any]


def normalize(source_slug: str, raw: dict[str, Any]) -> NormalizedActivity:
    """Dispatch normalization by source slug."""

    try:
        normalizer = _REGISTRY[source_slug]
    except KeyError as exc:
        raise ValidationError(
            f"Unknown source slug: {source_slug}"
        ) from exc

    return normalizer(raw)


# ----------------------------------------------------------------------
# GitHub
# ----------------------------------------------------------------------


def normalize_github(raw: dict[str, Any]) -> NormalizedActivity:
    """Normalize GitHub events."""

    event_type = raw["type"]

    repo = raw.get("repo", {})
    repo_name = repo.get("name", "Unknown Repository")

    payload = raw.get("payload", {})

    url = f"https://github.com/{repo_name}"

    # -----------------------------
    # Push Event
    # -----------------------------

    if event_type == "PushEvent":

        branch = (
            payload.get("ref", "")
            .replace("refs/heads/", "")
            or "main"
        )

        title = f"Pushed changes to {repo_name}"

        payload["branch"] = branch

        return NormalizedActivity(
            source_slug="github",
            external_id=raw["id"],
            type="Push",
            title=title,
            url=url,
            occurred_at=datetime.fromisoformat(
                raw["created_at"].replace("Z", "+00:00")
            ),
            raw_payload=raw,
        )

    # -----------------------------
    # Pull Request
    # -----------------------------

    if event_type == "PullRequestEvent":

        pr = payload.get("pull_request", {})

        return NormalizedActivity(
            source_slug="github",
            external_id=str(pr.get("id") or raw["id"]),
            type="Pull Request",
            title=pr.get(
                "title",
                f"Opened pull request in {repo_name}",
            ),
            url=pr.get("html_url", url),
            occurred_at=datetime.fromisoformat(
                raw["created_at"].replace("Z", "+00:00")
            ),
            raw_payload=raw,
        )

    # -----------------------------
    # Release
    # -----------------------------

    if event_type == "ReleaseEvent":

        release = payload.get("release", {})

        return NormalizedActivity(
            source_slug="github",
            external_id=str(release.get("id") or raw["id"]),
            type="Release",
            title=release.get(
                "name",
                release.get(
                    "tag_name",
                    f"Released {repo_name}",
                ),
            ),
            url=release.get(
                "html_url",
                f"{url}/releases",
            ),
            occurred_at=datetime.fromisoformat(
                raw["created_at"].replace("Z", "+00:00")
            ),
            raw_payload=raw,
        )

    # -----------------------------
    # Create
    # -----------------------------

    if event_type == "CreateEvent":

        ref_type = payload.get("ref_type", "branch")
        ref = payload.get("ref", "")

        return NormalizedActivity(
            source_slug="github",
            external_id=raw["id"],
            type="Create",
            title=f"Created {ref_type} '{ref}'",
            url=url,
            occurred_at=datetime.fromisoformat(
                raw["created_at"].replace("Z", "+00:00")
            ),
            raw_payload=raw,
        )

    # -----------------------------
    # Fallback
    # -----------------------------

    return NormalizedActivity(
        source_slug="github",
        external_id=raw["id"],
        type=event_type,
        title=event_type,
        url=url,
        occurred_at=datetime.fromisoformat(
            raw["created_at"].replace("Z", "+00:00")
        ),
        raw_payload=raw,
    )


# ----------------------------------------------------------------------
# X
# ----------------------------------------------------------------------


def normalize_x(raw: dict[str, Any]) -> NormalizedActivity:
    """Normalize one X post."""

    text = raw.get("text", "")

    title = (
        text[:77] + "..."
        if len(text) > 80
        else text
    )

    return NormalizedActivity(
        source_slug="x",
        external_id=raw["id"],
        type="Post",
        title=title or "Posted on X",
        url=f"https://x.com/i/web/status/{raw['id']}",
        occurred_at=datetime.fromisoformat(
            raw["created_at"].replace("Z", "+00:00")
        ),
        raw_payload=raw,
    )


# ----------------------------------------------------------------------
# LinkedIn
# ----------------------------------------------------------------------


def normalize_linkedin(raw: dict[str, Any]) -> NormalizedActivity:
    """Normalize one LinkedIn activity."""

    return NormalizedActivity(
        source_slug="linkedin",
        external_id=raw["external_id"],
        type=raw.get("type", "Post"),
        title=raw["title"],
        url=raw["url"],
        occurred_at=raw["occurred_at"],
        raw_payload=raw,
    )


_REGISTRY: dict[str, Callable[[dict[str, Any]], NormalizedActivity]] = {
    "github": normalize_github,
    "x": normalize_x,
    "linkedin": normalize_linkedin,
}