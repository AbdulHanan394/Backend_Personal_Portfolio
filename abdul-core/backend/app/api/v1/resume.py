"""Resume import endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_api_key
from app.schemas.resume import ResumeData
from app.services.resume_service import ResumeService

router = APIRouter(
    prefix="/resume",
    tags=["Resume"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/import")
async def import_resume(
    request: ResumeData,
    session: DbSession,
) -> dict:
    """
    Import a resume into the AI knowledge base.
    """

    service = ResumeService(session)

    await service.import_resume(request)

    return {
        "message": "Resume imported successfully."
    }