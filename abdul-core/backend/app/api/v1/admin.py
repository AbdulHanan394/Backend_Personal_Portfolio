"""Admin endpoints for manual operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_admin
from app.repositories.scheduler_log_repo import SchedulerLogRepository
from app.schemas.activity import ManualActivityCreate
from app.services.activity_service import ActivityService, get_activity_or_404, to_activity_response
from app.services.sync_service import SyncService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/sync/{source_slug}")
async def trigger_sync(source_slug: str, session: DbSession) -> dict:
    """Trigger an ad-hoc source sync."""

    result = await SyncService(session).run(source_slug)
    return {"data": {"source": source_slug, "processed": result.processed, "failed": result.failed}}


@router.get("/scheduler/status")
async def scheduler_status(session: DbSession) -> dict:
    """Return recent scheduler job logs."""

    logs = await SchedulerLogRepository(session).recent()
    return {
        "data": [
            {
                "id": str(log.id),
                "job_name": log.job_name,
                "started_at": log.started_at.isoformat(),
                "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                "status": log.status,
                "items_processed": log.items_processed,
                "items_failed": log.items_failed,
                "error_message": log.error_message,
            }
            for log in logs
        ]
    }


@router.post("/activities/manual")
async def create_manual_activity(request: ManualActivityCreate, session: DbSession) -> dict:
    """Insert a manual activity, primarily for LinkedIn v1."""

    activity = await ActivityService(session).insert_manual(request)
    await session.commit()
    refreshed = await get_activity_or_404(session, activity.id)
    return {"data": to_activity_response(refreshed).model_dump()}


@router.post("/activities/{activity_id}/retry")
async def retry_activity(activity_id: UUID, session: DbSession) -> dict:
    """Retry a failed activity from the current persisted stage."""

    activity = await get_activity_or_404(session, activity_id)
    service = ActivityService(session)
    if activity.status in {"normalized", "failed"}:
        activity = await service.enrich_activity(activity)
    if activity.status == "summarized":
        activity = await service.embed_and_publish(activity)
    await session.commit()
    return {"data": to_activity_response(activity).model_dump()}

