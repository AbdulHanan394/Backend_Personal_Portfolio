"""Project read endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, Pagination, require_api_key
from app.middleware.error_handler import NotFoundError
from app.repositories.project_repo import ProjectRepository
from app.schemas.common import Meta
from app.services.activity_service import to_activity_response

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("")
async def list_projects(session: DbSession, pagination: Pagination) -> dict:
    """Return projects with rolled-up activities."""

    projects, total = await ProjectRepository(session).list_all(
        limit=pagination.limit, offset=pagination.offset
    )
    return {
        "data": [_project_payload(project) for project in projects],
        "meta": Meta(total=total, limit=pagination.limit, offset=pagination.offset).model_dump(),
    }


@router.get("/{project_id}")
async def get_project(project_id: UUID, session: DbSession) -> dict:
    """Return one project with activities."""

    project = await ProjectRepository(session).get(project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return {"data": _project_payload(project)}


def _project_payload(project) -> dict:
    """Shape a project response."""

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "repo_url": project.repo_url,
        "live_url": project.live_url,
        "status": project.status,
        "activities": [
            to_activity_response(activity).model_dump()
            for activity in project.activities
            if activity.status == "published"
        ],
    }

