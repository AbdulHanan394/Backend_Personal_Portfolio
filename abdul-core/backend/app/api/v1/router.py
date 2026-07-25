"""Aggregate all v1 API routers."""

from fastapi import APIRouter

from app.api.v1 import (
    activities,
    admin,
    assistant,
    auth,
    health,
    projects,
    resume,
    search,
    sources,
)

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(activities.router, prefix="/activities", tags=["activities"])
router.include_router(sources.router, prefix="/sources", tags=["sources"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])

# NEW
router.include_router(resume.router)