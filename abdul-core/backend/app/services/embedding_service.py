"""Embedding generation and Chroma storage service."""

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


Source:
{activity.source.slug if activity.source else ""}


Activity Type:
{activity.type}


Category:
{activity.category or ""}


URL:
{activity.url or ""}


Skills / Tags:
{", ".join(
    tag.name
    for tag in activity.tags
)}


Technologies:
{", ".join(
    technology.name
    for technology in activity.technologies
)}


{social_links_text}


Raw Data:
{activity.raw_payload or ""}
""".strip()


        print("========== EMBEDDING DOCUMENT ==========")
        print(document)


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