"""Repository for project data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.models.project import Project


class ProjectRepository:
    """Data access for projects."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, *, limit: int, offset: int) -> tuple[list[Project], int]:
        """Return projects and total count."""

        stmt = select(Project).options(*_project_options()).limit(limit).offset(offset)
        count_stmt = select(func.count()).select_from(Project)
        return list(await self.session.scalars(stmt)), int(await self.session.scalar(count_stmt) or 0)

    async def get(self, project_id: UUID) -> Project | None:
        """Return one project."""

        return await self.session.scalar(
            select(Project).options(*_project_options()).where(Project.id == project_id)
        )


def _project_options() -> list:
    """Return eager-loading options needed for project API shaping."""

    return [
        selectinload(Project.activities).selectinload(Activity.source),
        selectinload(Project.activities).selectinload(Activity.tags),
        selectinload(Project.activities).selectinload(Activity.technologies),
    ]
