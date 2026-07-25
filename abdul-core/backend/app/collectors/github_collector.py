"""GitHub REST activity collector."""

from datetime import datetime

import httpx

from app.collectors.base import BaseCollector
from app.config.settings import get_settings
from app.middleware.error_handler import CollectorError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GitHubCollector(BaseCollector):
    """Collect recent GitHub public events."""

    source_slug = "github"

    allowed_event_types = {
        "PushEvent",
        "PullRequestEvent",
        "ReleaseEvent",
        "CreateEvent",
    }

    async def fetch_raw(self, since: datetime | None) -> list[dict]:
        settings = get_settings()

        if not settings.github_token:
            raise CollectorError("GITHUB_TOKEN is required")

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = (
            f"https://api.github.com/users/"
            f"{settings.github_username}/events"
        )

        events: list[dict] = []

        async with httpx.AsyncClient(timeout=30) as client:

            for _ in range(5):

                response = await client.get(
                    url,
                    headers=headers,
                )

                if response.status_code >= 400:
                    raise CollectorError(
                        f"GitHub API returned {response.status_code}"
                    )

                remaining = int(
                    response.headers.get(
                        "X-RateLimit-Remaining",
                        "999",
                    )
                )

                for item in response.json():

                    if item.get("type") not in self.allowed_event_types:
                        continue

                    created_at = datetime.fromisoformat(
                        item["created_at"].replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    if since and created_at <= since:
                        continue

                    if item["type"] == "PushEvent":
                        await self._attach_compare_data(
                            client,
                            headers,
                            item,
                        )

                    events.append(item)

                if remaining < 5:
                    logger.warning(
                        "github_rate_limit_low",
                        remaining=remaining,
                    )
                    break

                next_url = _next_link(
                    response.headers.get("Link", "")
                )

                if not next_url:
                    break

                url = next_url

        return events

    async def _attach_compare_data(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        event: dict,
    ) -> None:
        """
        Fetch compare information for PushEvents.

        This enriches the payload with:
        - total commits
        - commit messages
        - changed files
        - additions/deletions
        """

        payload = event.get("payload", {})

        before = payload.get("before")
        head = payload.get("head")

        repo_name = event["repo"]["name"]

        if not before or not head:
            return

        url = (
            f"https://api.github.com/repos/"
            f"{repo_name}/compare/"
            f"{before}...{head}"
        )

        try:

            response = await client.get(
                url,
                headers=headers,
            )

            if response.status_code >= 400:
                return

            compare = response.json()

            payload["compare"] = {
                "total_commits": compare.get(
                    "total_commits",
                    0,
                ),
                "commits": [
                    {
                        "sha": commit["sha"],
                        "message": commit["commit"]["message"],
                        "author": commit["commit"]["author"]["name"],
                    }
                    for commit in compare.get(
                        "commits",
                        [],
                    )
                ],
                "files": [
                    {
                        "filename": file["filename"],
                        "status": file["status"],
                        "additions": file["additions"],
                        "deletions": file["deletions"],
                        "changes": file["changes"],
                    }
                    for file in compare.get(
                        "files",
                        [],
                    )
                ],
            }

        except Exception as exc:
            logger.warning(
                "compare_api_failed",
                error=str(exc),
            )


def _next_link(link_header: str) -> str | None:

    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")

    return None