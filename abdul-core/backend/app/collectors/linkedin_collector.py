"""LinkedIn collector stub."""

from datetime import datetime

from app.collectors.base import BaseCollector
from app.middleware.error_handler import CollectorNotImplementedError


class LinkedInCollector(BaseCollector):
    """Intentionally disabled LinkedIn collector."""

    source_slug = "linkedin"

    async def fetch_raw(self, since: datetime | None) -> list[dict]:
        """Raise because LinkedIn personal activity collection is not available in v1."""

        raise CollectorNotImplementedError(
            "LinkedIn does not provide general personal-activity API access; use manual admin insertion."
        )

