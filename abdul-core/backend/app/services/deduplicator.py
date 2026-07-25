"""Deduplicate activities before insertion."""

from uuid import UUID

from app.repositories.activity_repo import ActivityRepository


class Deduplicator:
    """Database-backed deduplication service."""

    def __init__(self, activity_repo: ActivityRepository) -> None:
        self.activity_repo = activity_repo

    async def is_duplicate(self, source_id: UUID, external_id: str) -> bool:
        """Return whether the activity already exists."""

        return await self.activity_repo.exists(source_id, external_id)

