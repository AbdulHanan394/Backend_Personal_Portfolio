"""Activity pipeline and response shaping service."""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.source import Source

from app.repositories.activity_repo import ActivityRepository
from app.repositories.source_repo import SourceRepository

from app.schemas.activity import (
    ActivityResponse,
    ManualActivityCreate,
)

from app.services.ai_processor import AIProcessor
from app.services.deduplicator import Deduplicator
from app.services.embedding_service import EmbeddingService
from app.services.normalizer import NormalizedActivity

from app.utils.time import utc_now

import asyncio

try:
    from google.api_core.exceptions import GoogleAPICallError, ResourceExhausted
except ImportError:  # pragma: no cover - library may not be installed in all envs
    GoogleAPICallError = ResourceExhausted = ()  # type: ignore[assignment]

AI_ENRICHMENT_EXCEPTIONS = tuple(
    exc
    for exc in (GoogleAPICallError, ResourceExhausted, asyncio.TimeoutError, TimeoutError)
    if isinstance(exc, type)
) or (Exception,)


class ActivityService:
    """Orchestrate activity persistence and enrichment."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:

        self.session = session
        self.activity_repo = ActivityRepository(session)
        self.source_repo = SourceRepository(session)


    async def insert_normalized(
        self,
        normalized: NormalizedActivity,
    ) -> Activity | None:

        source = await self._require_source(
            normalized.source_slug
        )

        deduplicator = Deduplicator(self.activity_repo)

        print("SOURCE ID:", source.id)
        print("EXTERNAL ID:", normalized.external_id)

        is_dup = await deduplicator.is_duplicate(
            source.id,
            normalized.external_id,
          )

        print("IS DUPLICATE:", is_dup)

        if is_dup:
         return None


        activity = Activity(
            source_id=source.id,
            external_id=normalized.external_id,
            type=normalized.type,
            title=normalized.title,
            raw_payload=normalized.raw_payload,
            url=normalized.url,
            occurred_at=normalized.occurred_at,
            status="normalized",
        )


        created = await self.activity_repo.create(activity)

        await self.session.flush()


        created = await self.activity_repo.get(
            created.id
        )


        if created is None:
            raise RuntimeError(
                "Failed to reload activity"
            )


        return created



    async def insert_manual(
        self,
        request: ManualActivityCreate,
    ) -> Activity:
        """
        Insert manual portfolio/resume data.
        Includes social links in searchable content.
        """


        source = await self._require_source(
            "portfolio"
        )


        technologies = [
            await self.activity_repo.get_or_create_technology(
                name
            )
            for name in request.technologies
        ]


        tags = [
            await self.activity_repo.get_or_create_tag(
                name
            )
            for name in request.tags
        ]


        payload = (
            request.raw_payload
            or request.model_dump(
                mode="json"
            )
        )


        social_links = payload.get(
            "social_links",
            {}
        )


        enhanced_summary = f"""
{request.summary}


Social Links:

GitHub:
{social_links.get("github", "")}

LinkedIn:
{social_links.get("linkedin", "")}

X:
{social_links.get("x", "")}

Portfolio:
{social_links.get("portfolio", "")}
"""


        activity = Activity(

            source_id=source.id,

            external_id=str(
                uuid4()
            ),

            type=request.type,

            title=request.title,

            summary=enhanced_summary.strip(),

            category=request.category,

            raw_payload=payload,

            url=social_links.get(
                "linkedin",
                ""
            ),

            occurred_at=utc_now(),

            status="summarized",

            tags=tags,

            technologies=technologies,
        )


        self.session.add(activity)

        await self.session.flush()


        created = await self.activity_repo.get(
            activity.id
        )


        if created is None:
            raise RuntimeError(
                "Failed to reload activity"
            )


        return created



    async def enrich_activity(
        self,
        activity: Activity,
        ai_processor: AIProcessor | None = None,
    ) -> Activity:

        try:
            enrichment = await (
                ai_processor or AIProcessor()
            ).enrich(activity)

            activity.summary = enrichment.summary
            activity.category = enrichment.category

            activity.tags.clear()
            activity.technologies.clear()

            for tag_name in enrichment.tags:
                activity.tags.append(
                    await self.activity_repo.get_or_create_tag(tag_name)
                )

            for technology_name in enrichment.technologies:
                activity.technologies.append(
                    await self.activity_repo.get_or_create_technology(
                        technology_name
                    )
                )

        except AI_ENRICHMENT_EXCEPTIONS as exc:
            print(f"AI enrichment failed: {exc}")

            activity.summary = self._build_fallback_summary(activity)
            activity.category = "Other"

            activity.tags.clear()
            activity.technologies.clear()

            for tag_name in self._build_fallback_tags(activity):
                activity.tags.append(
                    await self.activity_repo.get_or_create_tag(tag_name)
                )

            for technology_name in self._build_fallback_technologies(activity):
                activity.technologies.append(
                    await self.activity_repo.get_or_create_technology(
                        technology_name
                    )
                )

        activity.status = "summarized"

        await self.session.flush()

        return activity


    def _build_fallback_summary(
        self,
        activity: Activity,
    ) -> str:

        payload = activity.raw_payload or {}

        if activity.type == "Push":
            compare = payload.get("payload", {}).get("compare", {})

            commits = compare.get("commits", [])
            files = compare.get("files", [])

            messages = [
                c.get("message")
                for c in commits
                if c.get("message")
            ]

            filenames = [
                f.get("filename")
                for f in files
                if f.get("filename")
            ]

            repo = payload.get("repo", {}).get("name", "")

            parts = []

            if repo:
                parts.append(f"Updated repository {repo}.")

            if messages:
                parts.append(
                    "Commits: " + ", ".join(messages[:3]) + "."
                )

            if filenames:
                parts.append(
                    "Files changed: "
                    + ", ".join(filenames[:5])
                    + "."
                )

            return " ".join(parts)

        elif activity.type == "Create":

            ref = payload.get("payload", {}).get("ref")
            description = payload.get("payload", {}).get("description")

            text = f"Created branch '{ref}'."

            if description:
                text += f" Repository description: {description}"

            return text

        return activity.title


    def _build_fallback_technologies(
        self,
        activity: Activity,
    ) -> set[str]:

        payload = activity.raw_payload or {}

        files = (
            payload.get("payload", {})
            .get("compare", {})
            .get("files", [])
        )

        techs: set[str] = set()

        for file in files:
            name = file.get("filename", "").lower()

            if name.endswith(".py"):
                techs.add("Python")

            elif name.endswith(".jsx") or name.endswith(".tsx"):
                techs.add("React")

            elif name.endswith(".ts"):
                techs.add("TypeScript")

            elif name.endswith(".js"):
                techs.add("JavaScript")

            elif "dockerfile" in name:
                techs.add("Docker")

            elif name.endswith(".sql"):
                techs.add("SQL")

        return techs


    def _build_fallback_tags(
        self,
        activity: Activity,
    ) -> set[str]:

        tags: set[str] = set()

        if activity.type == "Push":
            tags.add("GitHub")
            tags.add("Code")

        elif activity.type == "Create":
            tags.add("GitHub")
            tags.add("Repository")

        return tags


    async def embed_and_publish(
        self,
        activity: Activity,
    ) -> Activity:


        await EmbeddingService(
            self.session
        ).embed_activity(activity)


        activity.status = "published"


        await self.session.flush()


        return activity



    async def _require_source(
        self,
        slug: str,
    ) -> Source:


        source = await self.source_repo.get_by_slug(
            slug
        )


        if source is None:

            from app.middleware.error_handler import ValidationError

            raise ValidationError(
                f"Unknown source: {slug}"
            )


        return source



def to_activity_response(
    activity: Activity,
) -> ActivityResponse:


    return ActivityResponse(

        id=str(activity.id),

        source=activity.source.slug,

        type=activity.type,

        title=activity.title,

        summary=activity.summary,

        tags=[
            tag.name
            for tag in activity.tags
        ],

        technologies=[
            technology.name
            for technology in activity.technologies
        ],

        category=activity.category,

        date=activity.occurred_at.date().isoformat(),

        url=activity.url,
    )
async def get_activity_or_404(
    session: AsyncSession,
    activity_id: UUID,
) -> Activity:
    """
    Return activity or raise not found.
    """

    from app.middleware.error_handler import NotFoundError

    activity = await ActivityRepository(session).get(
        activity_id
    )

    if activity is None:
        raise NotFoundError(
            "Activity not found"
        )

    return activity