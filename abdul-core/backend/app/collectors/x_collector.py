"""X API v2 activity collector."""

from datetime import datetime

import httpx

from app.collectors.base import BaseCollector
from app.config.settings import get_settings
from app.middleware.error_handler import CollectorError


class XCollector(BaseCollector):
    """Collect original posts from X."""

    source_slug = "x"
    _cached_user_id: str | None = None

    async def fetch_raw(self, since: datetime | None) -> list[dict]:
        """Fetch recent original posts from X."""

        settings = get_settings()
        if not settings.x_bearer_token:
            raise CollectorError("X_BEARER_TOKEN is required for X collection")
        headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            user_id = await self._get_user_id(client, headers)
            params = {
                "exclude": "replies,retweets",
                "tweet.fields": "created_at,public_metrics,entities",
                "max_results": "50",
            }
            response = await client.get(
                f"https://api.x.com/2/users/{user_id}/tweets",
                headers=headers,
                params=params,
            )
            if response.status_code >= 400:
                raise CollectorError(f"X API returned {response.status_code}")
            tweets = response.json().get("data", [])
        if since is None:
            return tweets
        return [
            tweet
            for tweet in tweets
            if datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")) > since
        ]

    async def _get_user_id(self, client: httpx.AsyncClient, headers: dict[str, str]) -> str:
        """Resolve and cache the configured username's numeric X user ID."""

        if self._cached_user_id:
            return self._cached_user_id
        settings = get_settings()
        response = await client.get(
            f"https://api.x.com/2/users/by/username/{settings.x_username}",
            headers=headers,
        )
        if response.status_code >= 400:
            raise CollectorError(f"X user lookup returned {response.status_code}")
        self._cached_user_id = response.json()["data"]["id"]
        return self._cached_user_id

