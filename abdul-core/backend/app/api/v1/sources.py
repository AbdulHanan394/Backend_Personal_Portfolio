"""Source read endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_api_key
from app.repositories.source_repo import SourceRepository

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("")
async def list_sources(session: DbSession) -> dict:
    """Return known source platforms."""

    sources = await SourceRepository(session).list_all()
    return {
        "data": [
            {
                "id": str(source.id),
                "slug": source.slug,
                "display_name": source.display_name,
                "is_active": source.is_active,
                "last_synced_at": source.last_synced_at.isoformat() if source.last_synced_at else None,
            }
            for source in sources
        ]
    }

