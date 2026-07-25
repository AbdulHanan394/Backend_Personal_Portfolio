"""Collector-to-storage synchronization service."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.linkedin_collector import LinkedInCollector
from app.collectors.x_collector import XCollector
from app.middleware.error_handler import ValidationError
from app.repositories.source_repo import SourceRepository
from app.services.activity_service import ActivityService
from app.services.normalizer import normalize
from app.utils.time import utc_now


@dataclass
class SyncResult:
    """Summary of one sync run."""

    processed: int = 0
    failed: int = 0


class SyncService:
    """Run source collectors and persist normalized activities."""

    collectors: dict[str, type[BaseCollector]] = {
        "github": GitHubCollector,
        "x": XCollector,
        "linkedin": LinkedInCollector,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, source_slug: str) -> SyncResult:
        """Run one collector through normalization, enrichment and storage."""

        source = await SourceRepository(self.session).get_by_slug(source_slug)
        if source is None:
            raise ValidationError(f"Unknown source: {source_slug}")

        try:
            collector = self.collectors[source_slug]()
        except KeyError as exc:
            raise ValidationError(
                f"No collector registered for source: {source_slug}"
            ) from exc

        raw_items = await collector.fetch_raw(source.last_synced_at)

        activity_service = ActivityService(self.session)
        result = SyncResult()

        for raw in raw_items:
            try:
                # --------------------------------------------------
                # Normalize
                # --------------------------------------------------
                normalized = normalize(source_slug, raw)

                # --------------------------------------------------
                # Store in PostgreSQL
                # --------------------------------------------------
                activity = await activity_service.insert_normalized(normalized)

                # Duplicate activity
                if activity is None:
                    continue

                # --------------------------------------------------
                # AI ENRICHMENT (OPTIONAL)
                # --------------------------------------------------
                try:
                    await activity_service.enrich_activity(activity)

                except Exception as exc:
                    print(f"AI enrichment failed: {exc}")

                    # Fallback summary so RAG still works
                    activity.summary = activity.title
                    activity.category = "Other"

                    # Preserve pipeline
                    activity.status = "summarized"

                    await self.session.flush()

                # --------------------------------------------------
                # EMBEDDING + PUBLISH (OPTIONAL)
                # --------------------------------------------------
                try:
                    await activity_service.embed_and_publish(activity)

                except Exception as exc:
                    print(f"Embedding failed: {exc}")

                    # Keep the activity searchable later
                    activity.status = "summarized"

                    await self.session.flush()

                result.processed += 1

            except Exception as exc:
                result.failed += 1
                print(f"Failed to process activity: {exc}")

        if raw_items:
            source.last_synced_at = utc_now()

        await self.session.commit()

        return result