"""Repository for activity data access."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.models.embedding import Embedding
from app.models.source import Source
from app.models.tag import Tag
from app.models.technology import Technology


class ActivityRepository:
    """Data access for activities and related labels."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, source_id: UUID, external_id: str) -> bool:
        """Return whether a source/external id pair already exists."""

        stmt = (
            select(func.count())
            .select_from(Activity)
            .where(
                Activity.source_id == source_id,
                Activity.external_id == external_id,
            )
        )

        count = await self.session.scalar(stmt)

        print(
            f"[ActivityRepository.exists] source_id={source_id} "
            f"external_id={external_id!r} count={count}"
        )

        return bool(count and count > 0)

    async def create(self, activity: Activity) -> Activity:
        """Persist a new activity."""

        self.session.add(activity)
        await self.session.flush()
        return activity

    async def get(self, activity_id: UUID) -> Activity | None:
        """Return one activity with display relationships loaded."""

        return await self.session.scalar(_activity_display_query().where(Activity.id == activity_id))

    async def list_published(
        self,
        *,
        source: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Activity], int]:
        """Return published activities and total count."""

        stmt = _activity_display_query().join(Activity.source).where(Activity.status == "published")
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Activity).join(Activity.source).where(
            Activity.status == "published"
        )
        if source and source != "all":
            stmt = stmt.where(Source.slug == source)
            count_stmt = count_stmt.where(Source.slug == source)
        if category:
            stmt = stmt.where(Activity.category == category)
            count_stmt = count_stmt.where(Activity.category == category)
        stmt = stmt.order_by(Activity.occurred_at.desc()).limit(limit).offset(offset)
        activities = list(await self.session.scalars(stmt))
        total = int(await self.session.scalar(count_stmt) or 0)
        return activities, total

    async def list_by_ids(self, ids: Sequence[UUID]) -> list[Activity]:
        """Return published activities matching IDs."""

        if not ids:
            return []
        result = await self.session.scalars(
            _activity_display_query().where(Activity.id.in_(ids), Activity.status == "published")
        )
        return list(result)

    async def get_or_create_tag(self, name: str) -> Tag:
        """Return an existing tag or create it."""

        tag = await self.session.scalar(select(Tag).where(Tag.name == name))
        if tag:
            return tag
        tag = Tag(name=name)
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def get_or_create_technology(self, name: str) -> Technology:
        """Return an existing technology or create it."""

        technology = await self.session.scalar(select(Technology).where(Technology.name == name))
        if technology:
            return technology
        technology = Technology(name=name)
        self.session.add(technology)
        await self.session.flush()
        return technology

    async def create_embedding(self, embedding: Embedding) -> Embedding:
        """Persist an embedding tracking row."""

        self.session.add(embedding)
        await self.session.flush()
        return embedding


def _activity_display_query() -> Select[tuple[Activity]]:
    """Build a query with all relationships needed for API display."""

    return select(Activity).options(
        selectinload(Activity.source),
        selectinload(Activity.tags),
        selectinload(Activity.technologies),
        selectinload(Activity.projects),
    )