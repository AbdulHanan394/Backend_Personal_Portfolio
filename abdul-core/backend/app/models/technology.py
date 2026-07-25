"""Technology ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.activity import activity_technologies

if TYPE_CHECKING:
    from app.models.activity import Activity


class Technology(UUIDPrimaryKeyMixin, Base):
    """Technology extracted from an activity."""

    __tablename__ = "technologies"

    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    activities: Mapped[list["Activity"]] = relationship(
    secondary="activity_technologies",
    back_populates="technologies",
    lazy="selectin",
    )

