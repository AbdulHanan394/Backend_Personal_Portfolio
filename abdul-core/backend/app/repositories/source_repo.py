"""Repository for source rows."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source


class SourceRepository:
    """Data access for sources."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_slug(self, slug: str) -> Source | None:
        """Return one source by slug."""

        return await self.session.scalar(select(Source).where(Source.slug == slug))

    async def list_all(self) -> list[Source]:
        """Return all sources."""

        result = await self.session.scalars(select(Source).order_by(Source.display_name))
        return list(result)

