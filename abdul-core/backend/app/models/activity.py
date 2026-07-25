"""Activity ORM model and tag/technology associations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.embedding import Embedding
    from app.models.project import Project
    from app.models.source import Source
    from app.models.tag import Tag
    from app.models.technology import Technology


activity_tags = Table(
    "activity_tags",
    Base.metadata,
    Column("activity_id", UUID(as_uuid=True), ForeignKey("activities.id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True),
)

activity_technologies = Table(
    "activity_technologies",
    Base.metadata,
    Column("activity_id", UUID(as_uuid=True), ForeignKey("activities.id"), primary_key=True),
    Column("technology_id", UUID(as_uuid=True), ForeignKey("technologies.id"), primary_key=True),
)


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A normalized and enriched activity from an external platform."""

    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_activity_source_external"),
        Index("ix_activities_source_occurred", "source_id", "occurred_at"),
        Index("ix_activities_status", "status"),
        Index("ix_activities_raw_payload_gin", "raw_payload", postgresql_using="gin"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)
    url: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="collected")
    error_message: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="activities")
    tags: Mapped[list[Tag]] = relationship(
    secondary=activity_tags,
    back_populates="activities",
    lazy="selectin",
    )

    technologies: Mapped[list[Technology]] = relationship(
    secondary=activity_technologies,
    back_populates="activities",
    lazy="selectin",
    )
    projects: Mapped[list[Project]] = relationship(
        secondary="activity_projects", back_populates="activities"
    )
    embedding: Mapped[Embedding | None] = relationship(back_populates="activity")
