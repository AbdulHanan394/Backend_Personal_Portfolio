"""Activity read endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, Pagination, require_api_key
from app.repositories.activity_repo import ActivityRepository
from app.schemas.common import ListEnvelope, Meta
from app.services.activity_service import get_activity_or_404, to_activity_response

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("")
async def list_activities(
    session: DbSession,
    pagination: Pagination,
    source: Annotated[str, Query(pattern="^(all|github|linkedin|x|manual)$")] = "all",
    category: str | None = None,
    sort: Annotated[str, Query(pattern="^recent$")] = "recent",
) -> dict:
    """Return published activities in the portfolio contract shape."""

    activities, total = await ActivityRepository(session).list_published(
        source=source,
        category=category,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return ListEnvelope(
        data=[to_activity_response(activity) for activity in activities],
        meta=Meta(total=total, limit=pagination.limit, offset=pagination.offset),
    ).model_dump()


@router.get("/{activity_id}")
async def get_activity(activity_id: UUID, session: DbSession) -> dict:
    """Return one published activity."""

    activity = await get_activity_or_404(session, activity_id)
    return {"data": to_activity_response(activity).model_dump()}

