"""RAG assistant endpoint."""

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_api_key
from app.schemas.assistant import AssistantQuery
from app.services.rag_service import RAGService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/query")
async def query_assistant(request: AssistantQuery, session: DbSession) -> dict:
    """Answer a question using retrieved activity context."""

    answer = await RAGService(session).answer(request.question, request.history)
    return {"answer": answer}

