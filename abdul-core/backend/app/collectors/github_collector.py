"""GitHub REST activity collector."""

import asyncio
from datetime import datetime, timezone

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

        # GitHub timestamps are always tz-aware (UTC). If `since` came in
        # naive (e.g. from a DB column without tz info), comparing it below
        # raises TypeError and — depending on how that's handled upstream —
        # can silently result in zero events being collected. Normalize it.
        if since is not None and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = (
            f"{settings.github_api_url}/users/"
            f"{settings.github_username}/events"
            f"?per_page={settings.github_events_per_page}"
        )

        events: list[dict] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # NOTE: repo_data is fetched but never attached to the return
            # value, so it currently has no effect on what gets synced.
            # Kept here in case callers rely on the side effect (e.g. a
            # future normalize() step), but flagging it since it's dead
            # weight as written — safe to remove if truly unused.
            repo_data = await self._fetch_repositories(client, headers)
            logger.debug("github_repos_fetched", count=len(repo_data))

            for page_num in range(settings.github_max_pages):

                response = await client.get(url, headers=headers)

                if response.status_code >= 400:
                    raise CollectorError(
                        f"GitHub API returned {response.status_code}"
                    )

                remaining = int(
                    response.headers.get("X-RateLimit-Remaining", "999")
                )

                page_items = response.json()
                reached_since = False

                for item in page_items:

                    if item.get("type") not in self.allowed_event_types:
                        continue

                    created_at = datetime.fromisoformat(
                        item["created_at"].replace("Z", "+00:00")
                    )

                    if since and created_at <= since:
                        # Events come back newest-first, so once we hit one
                        # that's at/before `since`, every remaining event on
                        # this page (and on later pages) is also old.
                        # `continue`-ing here just wastes API calls; `break`
                        # out and stop paginating entirely.
                        reached_since = True
                        break

                    if item["type"] == "PushEvent":
                        await self._attach_compare_data(client, headers, item)

                    events.append(item)

                logger.debug(
                    "github_page_fetched",
                    page=page_num,
                    fetched=len(page_items),
                    kept=len(events),
                )

                if reached_since:
                    break

                if remaining < 5:
                    logger.warning("github_rate_limit_low", remaining=remaining)
                    break

                next_url = _next_link(response.headers.get("Link", ""))

                if not next_url:
                    break

                url = next_url

        logger.info("github_fetch_complete", since=since, total=len(events))

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

        settings = get_settings()

        url = (
            f"{settings.github_api_url}/repos/"
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

    async def _fetch_repo_languages(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        repo: str,
    ) -> dict:

        settings = get_settings()

        try:
            response = await client.get(
                f"{settings.github_api_url}/repos/{repo}/languages",
                headers=headers,
            )

            if response.status_code >= 400:
                return {}

            return response.json()

        except Exception as exc:
            logger.warning("languages_fetch_failed", repo=repo, error=str(exc))
            return {}

    async def _fetch_repo_topics(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        repo: str,
    ) -> list[str]:

        settings = get_settings()

        try:
            response = await client.get(
                f"{settings.github_api_url}/repos/{repo}/topics",
                headers={
                    **headers,
                    "Accept": "application/vnd.github+json",
                },
            )

            if response.status_code >= 400:
                return []

            return response.json().get("names", [])

        except Exception as exc:
            logger.warning("topics_fetch_failed", repo=repo, error=str(exc))
            return []

    async def _fetch_repositories(
        self,
        client: httpx.AsyncClient,
        headers: dict,
    ) -> list[dict]:

        settings = get_settings()

        repos: list[dict] = []
        url = (
            f"{settings.github_api_url}/users/"
            f"{settings.github_username}/repos?per_page=100"
        )

        # Paginate instead of only reading the first page of repos.
        while url:
            try:
                response = await client.get(url, headers=headers)
            except Exception as exc:
                logger.warning("repos_fetch_failed", error=str(exc))
                break

            if response.status_code >= 400:
                break

            repos.extend(response.json())
            url = _next_link(response.headers.get("Link", ""))

        # Fetch languages/topics concurrently rather than one repo at a time.
        async def _enrich(repo: dict) -> None:
            languages, topics = await asyncio.gather(
                self._fetch_repo_languages(client, headers, repo["full_name"]),
                self._fetch_repo_topics(client, headers, repo["full_name"]),
            )
            repo["languages"] = languages
            repo["topics"] = topics

        if repos:
            await asyncio.gather(*(_enrich(repo) for repo in repos))

        return repos


def _next_link(link_header: str) -> str | None:

    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")

    return None