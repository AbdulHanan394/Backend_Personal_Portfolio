"""Semantic search endpoint."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_api_key
from app.services.rag_service import RAGService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("")
async def semantic_search(
    session: DbSession,
    q: str = Query(min_length=1),
    source: str | None = None,
    category: str | None = None,
    limit: int = Query(default=10, ge=1, le=25),
) -> dict:
    """Return semantic search matches over published activities."""

    matches = await RAGService(session).search(q, source=source, category=category, limit=limit)
    return {"data": [match.model_dump() for match in matches]}

