"""Project response schemas."""

from pydantic import BaseModel

from app.schemas.activity import ActivityResponse


class ProjectResponse(BaseModel):
    """Portfolio-facing project shape with rolled-up activities."""

    id: str
    name: str
    description: str
    repo_url: str | None
    live_url: str | None
    status: str
    activities: list[ActivityResponse] = []

