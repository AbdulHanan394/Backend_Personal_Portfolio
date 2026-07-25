"""Activity request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityResponse(BaseModel):
    """Portfolio-facing activity response shape."""

    id: str
    source: str
    type: str
    title: str
    summary: str | None
    tags: list[str]
    technologies: list[str]
    category: str |None
    date: str
    url: str


class ManualActivityCreate(BaseModel):
    """Admin request for manually inserting an activity."""

    type: str
    title: str
    summary: str | None = None
    category: str |None = None

    url: str | None = None

    raw_payload: dict = Field(default_factory=dict)

    tags: list[str] = Field(default_factory=list, max_length=3)
    technologies: list[str] = Field(default_factory=list)

class ActivityDBView(BaseModel):
    """Internal activity view used by search results."""

    id: UUID
    title: str
    summary: str | None
    category: str | None
    occurred_at: datetime