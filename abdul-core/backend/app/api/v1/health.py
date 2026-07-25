"""Health check endpoints."""

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.deps import DbSession
from app.config.settings import get_settings
from app.database.chroma import get_chroma_collection

router = APIRouter()


@router.get("/health")
async def health(session: DbSession) -> dict:
    """Return liveness/readiness status for core dependencies."""

    await session.execute(text("select 1"))
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    try:
        await redis.ping()
    finally:
        await redis.aclose()
    get_chroma_collection().count()
    return {"data": {"status": "ok", "db": "ok", "redis": "ok", "chroma": "ok"}}

