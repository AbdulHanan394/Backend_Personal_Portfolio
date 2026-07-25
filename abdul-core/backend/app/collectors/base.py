"""Collector abstraction for source platform polling."""

from abc import ABC, abstractmethod
from datetime import datetime


class BaseCollector(ABC):
    """Base contract for all activity collectors."""

    source_slug: str

    @abstractmethod
    async def fetch_raw(self, since: datetime | None) -> list[dict]:
        """Return source-shaped raw activity dictionaries."""

