"""Activity tag ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.activity import activity_tags

if TYPE_CHECKING:
    from app.models.activity import Activity


class Tag(UUIDPrimaryKeyMixin, Base):
    """Human-readable label assigned to activities."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    activities: Mapped[list["Activity"]] = relationship(
    secondary="activity_tags",
    back_populates="tags",
    lazy="selectin",
    )   

