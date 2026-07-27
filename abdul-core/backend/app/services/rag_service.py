"""Retrieval augmented assistant service."""

import logging
import traceback
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings_client import EmbeddingsClient, SentenceTransformersEmbeddingsClient
from app.ai.llm_client import LLMClient
from app.ai.provider import get_llm
from app.ai.prompts.assistant_system_prompt import build_assistant_system_prompt
from app.database.chroma import get_chroma_collection
from app.middleware.error_handler import AIProcessingError
from app.repositories.activity_repo import ActivityRepository
from app.schemas.activity import ActivityResponse
from app.schemas.assistant import ChatMessage
from app.services.activity_service import to_activity_response

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 10
_FETCH_MULTIPLIER = 2  # over-fetch so distance filtering still leaves enough results
# Tune this against your collection's actual distance metric (L2 vs cosine) before
# relying on it — see caveat in review response. Higher distance = worse match.
_MAX_DISTANCE = 4.0


class AnswerResult(BaseModel):
    """Assistant answer plus the activities used to ground it."""

    answer: str
    activities: list[ActivityResponse]


class RAGService:
    """Semantic search and grounded assistant orchestration."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings_client: EmbeddingsClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.session = session
        self.embeddings_client = (
             embeddings_client
            or SentenceTransformersEmbeddingsClient()
        )
        self.llm_client = llm_client or get_llm()

    async def search(
        self,
        query: str,
        *,
        source: str | None = None,
        category: str | None = None,
        limit: int = 10,
        max_distance: float | None = None,
    ) -> list[ActivityResponse]:
        """Return matched activities for a semantic query, best match first."""

        if not query or not query.strip():
            return []

        limit = max(1, limit)
        fetch_n = limit * _FETCH_MULTIPLIER

        try:
            vector = await self.embeddings_client.embed(query)
        except Exception as exc:  # noqa: BLE001
            raise AIProcessingError(f"Failed to embed query: {exc}") from exc

        filters: list[dict[str, str]] = []
        if source and source != "all":
            filters.append({"source": source})
        if category:
            filters.append({"category": category})

        if len(filters) > 1:
            where: dict | None = {"$and": filters}
        elif filters:
            where = filters[0]
        else:
            where = None

        try:
            result = get_chroma_collection().query(
                query_embeddings=[vector],
                n_results=fetch_n,
                where=where,
            )
            logger.debug("Chroma query result: %s", result)
        except Exception as exc:  # noqa: BLE001
            raise AIProcessingError(f"Vector search failed: {exc}") from exc

        raw_ids = result.get("ids") or [[]]
        id_batch = raw_ids[0] if raw_ids else []

        raw_distances = result.get("distances") or [[]]
        distance_batch = raw_distances[0] if raw_distances else []
        if len(distance_batch) != len(id_batch):
            distance_batch = [None] * len(id_batch)

        ids: list[UUID] = []
        for item_id, distance in zip(id_batch, distance_batch):
            if max_distance is not None and distance is not None and distance > max_distance:
                continue
            try:
                ids.append(UUID(item_id))
            except (ValueError, TypeError, AttributeError):
                continue

        ids = ids[:limit]
        if not ids:
            return []

        activities = await ActivityRepository(self.session).list_by_ids(ids)
        logger.debug("UUIDs after filtering: %s", ids)
        logger.debug("Activities found: %d", len(activities))

        by_id = {activity.id: activity for activity in activities}
        return [to_activity_response(by_id[item_id]) for item_id in ids if item_id in by_id]

    @staticmethod
    def _build_context(matches: list[ActivityResponse]) -> str:
        """Build readable context for the LLM."""

        if not matches:
            return "No relevant information found."

        sections = []

        for item in matches:

            technologies = (
                ", ".join(item.technologies)
                if item.technologies
                else "None"
            )

            tags = (
                ", ".join(item.tags)
                if item.tags
                else "None"
            )

            sections.append(
                f"""
Title:
{item.title}

Summary:
{item.summary}

Category:
{item.category}

Source:
{item.source}

Technologies:
{technologies}

Tags:
{tags}

Date:
{item.date}

URL:
{item.url}
""".strip()
            )

        return "\n\n=============================\n\n".join(sections)

    async def answer(self, question: str, history: list[ChatMessage]) -> AnswerResult:
        """Answer a portfolio question using retrieved activity context.

        NOTE: this returns an AnswerResult (answer + cited activities)
        instead of a bare str. Update any existing callers accordingly.
        """

        if not question or not question.strip():
            raise AIProcessingError("Question must not be empty")

        matches = await self.search(question, limit=8, max_distance=_MAX_DISTANCE)
        unique = {}

        for activity in matches:
            key = (
                activity.title,
                activity.source,
                activity.category,
            )

            if key not in unique:
                unique[key] = activity

        matches = list(unique.values())
        context = self._build_context(matches)
        logger.debug("========== CONTEXT ==========\n%s\n=============================", context)

        system = build_assistant_system_prompt(context)
        logger.debug("========== SYSTEM ==========\n%s\n=============================", system)

        clipped_history = history[-_MAX_HISTORY_MESSAGES:] if history else []
        conversation = "\n".join(f"{item.role}: {item.content}" for item in clipped_history)

        prompt = f"""Conversation so far:
{conversation or "(none)"}

Current question:
{question}

Answer naturally using only the activities in the provided context. If the
context doesn't contain enough information to answer, say you don't know
instead of guessing."""
        import traceback

        try:
            print("Calling LLM...")
            
            answer_text = await self.llm_client.complete(
                system,
                prompt,
          )
            print("LLM Successfull...")
        except Exception:
            print("========== LLM ERROR ==========")
            traceback.print_exc()
            raise
        logger.debug("========== ANSWER ==========\n%s\n=============================", answer_text)

        return AnswerResult(answer=answer_text, activities=matches)