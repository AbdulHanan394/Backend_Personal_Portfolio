"""Embedding generation and Chroma storage service."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings_client import (
    EmbeddingsClient,
    SentenceTransformersEmbeddingsClient,
)

from app.config.settings import get_settings
from app.database.chroma import get_chroma_collection

from app.middleware.error_handler import EmbeddingError

from app.models.activity import Activity
from app.models.embedding import Embedding

from app.repositories.activity_repo import ActivityRepository

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embed activities and persist vector tracking rows."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings_client: EmbeddingsClient | None = None,
    ) -> None:

        self.session = session

        self.embeddings_client = (
            embeddings_client
            or SentenceTransformersEmbeddingsClient()
        )

        self.activity_repo = ActivityRepository(session)

    # -----------------------------
    # Raw payload extraction helpers
    # -----------------------------

    @staticmethod
    def _safe_payload(activity: Activity) -> dict:
        """Return activity.raw_payload as a dict, or {} if missing/non-dict.

        raw_payload can be None, a dict, or (for some sources) a plain
        string, so every extraction helper below routes through this
        instead of accessing activity.raw_payload directly.
        """

        payload = activity.raw_payload

        return payload if isinstance(payload, dict) else {}

    def _extract_repo_name(self, activity: Activity) -> str:
        """Extract the repository name, if present, from a GitHub event."""

        payload = self._safe_payload(activity)

        repo = payload.get("repo") or {}

        return repo.get("name", "") if isinstance(repo, dict) else ""

    def _extract_repo_description(self, activity: Activity) -> str:
        """Extract a repository description, if present."""

        payload = self._safe_payload(activity)

        return payload.get("description", "") or ""

    def _extract_compare(self, activity: Activity) -> dict:
        """Extract the compare block attached to GitHub PushEvents."""

        payload = self._safe_payload(activity)

        inner_payload = payload.get("payload") or {}

        if not isinstance(inner_payload, dict):
            return {}

        compare = inner_payload.get("compare") or {}

        return compare if isinstance(compare, dict) else {}

    def _extract_commit_messages(self, activity: Activity) -> str:
        """Extract up to 5 commit messages for this activity, if any."""

        compare = self._extract_compare(activity)
        commits = compare.get("commits", [])

        return "\n".join(
            f"- {commit.get('message', '')}"
            for commit in commits[:5]
        )

    def _extract_changed_files(self, activity: Activity) -> str:
        """Extract up to 10 changed filenames for this activity, if any."""

        compare = self._extract_compare(activity)
        files = compare.get("files", [])

        return "\n".join(
            f"- {file.get('filename', '')}"
            for file in files[:10]
        )

    def _extract_embedding_context(self, activity: Activity) -> str:
        """Extract additional low-noise context useful for embeddings.

        Repository name/description and commit/file details are already
        surfaced as their own document sections, so this is intentionally
        limited to repo topics and languages to avoid duplicating content
        (and diluting the resulting vector) elsewhere in the document.
        """

        payload = self._safe_payload(activity)

        lines = []

        topics = payload.get("topics")
        if topics:
            lines.append("Topics: " + ", ".join(topics))

        languages = payload.get("languages")
        if languages and isinstance(languages, dict):
            lines.append("Languages: " + ", ".join(languages.keys()))

        return "\n".join(lines)

    async def embed_activity(
        self,
        activity: Activity,
    ) -> Embedding:
        """
        Generate embedding from complete activity information
        and store it in ChromaDB.
        """

        # -----------------------------
        # Extract social links
        # -----------------------------

        social_links_text = ""

        if activity.raw_payload:

            if isinstance(activity.raw_payload, dict):

                payload = activity.raw_payload

                links = payload.get("social_links")

                if not links:
                    links = payload

                if activity.type == "social":

                    social_links_text = f"""
Profile Name:
{activity.title}

Profile URL:
{activity.url or ""}

Social Media Profiles:

GitHub:
{links.get("github", "")}

LinkedIn:
{links.get("linkedin", "")}

X:
{links.get("x", "")}

Portfolio:
{links.get("portfolio", "")}
"""

                else:

                    social_links_text = f"""
Social Media Profiles:

GitHub:
{links.get("github", "")}

LinkedIn:
{links.get("linkedin", "")}

X:
{links.get("x", "")}

Portfolio:
{links.get("portfolio", "")}
"""

            else:

                social_links_text = str(
                    activity.raw_payload
                )

        # -----------------------------
        # Create embedding document
        # -----------------------------

        document = f"""
Title:
{activity.title}


Summary:
{activity.summary or ""}


Repository:
{self._extract_repo_name(activity)}


Repository Description:
{self._extract_repo_description(activity)}


Source:
{activity.source.slug if activity.source else ""}


Activity Type:
{activity.type}


Category:
{activity.category or ""}


Tags:
{", ".join(
    tag.name
    for tag in activity.tags
)}


Technologies:
{", ".join(
    technology.name
    for technology in activity.technologies
)}


Commit Messages:
{self._extract_commit_messages(activity)}


Changed Files:
{self._extract_changed_files(activity)}


Important Details:
{self._extract_embedding_context(activity)}


{social_links_text}
""".strip()

        logger.info(
            "Embedding activity %s",
            activity.title,
        )

        try:

            # Generate vector

            embedding_vector = await (
                self.embeddings_client.embed(
                    document
                )
            )

            collection = get_chroma_collection()

            # Store vector

            collection.upsert(

                ids=[
                    str(activity.id)
                ],

                embeddings=[
                    embedding_vector
                ],

                documents=[
                    document
                ],

                metadatas=[

                    {
                        "activity_id":
                        str(activity.id),

                        "title":
                        activity.title,

                        "type":
                        activity.type,

                        "source":
                        (
                            activity.source.slug
                            if activity.source
                            else ""
                        ),

                        "category":
                        activity.category or "",

                        "url":
                        activity.url or "",

                        "tags":
                        ",".join(
                            tag.name
                            for tag in activity.tags
                        ),

                        "technologies":
                        ",".join(
                            tech.name
                            for tech in activity.technologies
                        ),

                        "occurred_at":
                        activity.occurred_at.isoformat(),

                    }

                ],
            )

        except Exception as exc:

            raise EmbeddingError(
                f"Embedding failed for activity {activity.id}: {exc}"
            ) from exc

        settings = get_settings()

        return await self.activity_repo.create_embedding(

            Embedding(

                activity_id=activity.id,

                chroma_id=str(activity.id),

                model_name=settings.embedding_model,

                dims=len(
                    embedding_vector
                ),

            )

        )