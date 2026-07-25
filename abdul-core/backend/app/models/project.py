"""Project ORM model and activity association."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import Activity


activity_projects = Table(
    "activity_projects",
    Base.metadata,
    Column("activity_id", UUID(as_uuid=True), ForeignKey("activities.id"), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True),
)


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Portfolio project that can roll up activities."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repo_url: Mapped[str | None] = mapped_column(String)
    live_url: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")

    activities: Mapped[list[Activity]] = relationship(
        secondary=activity_projects, back_populates="projects"
    )
