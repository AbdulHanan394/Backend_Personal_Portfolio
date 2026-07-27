"""Collector-to-storage synchronization service."""

from dataclasses import dataclass
import logging

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

logger = logging.getLogger(__name__)


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
        """Run one collector through the full processing pipeline."""

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
        logger.info("Fetched %d raw items", len(raw_items))
        activity_service = ActivityService(self.session)
        result = SyncResult()

        for index, raw in enumerate(raw_items, start=1):
            logger.debug("Processing #%d", index)
            try:
                # ---------------------------------------------
                # STEP 1 - Normalize
                # ---------------------------------------------
                normalized = normalize(source_slug, raw)
                logger.debug("Normalized: %s", normalized.external_id)

                # ---------------------------------------------
                # STEP 2 - Store in PostgreSQL
                # ---------------------------------------------
                activity = await activity_service.insert_normalized(normalized)
                print("INSERT:", activity)
                # Skip duplicates
                if activity is None:
                    continue

                # ---------------------------------------------
                # STEP 3 - AI Enrichment
                # ---------------------------------------------
                try:
                    activity = await activity_service.enrich_activity(activity)
                    print("ENRICH:", activity.id)
                except Exception:
                    logger.exception(
                        "AI enrichment failed for activity %s",
                        activity.id,
                    )

                    activity.summary = activity.title
                    activity.category = "other"
                    activity.status = "summarized"

                    await self.session.flush()

                # ---------------------------------------------
                # STEP 4 - Embedding + Publish
                # ---------------------------------------------
                try:
                    activity = await activity_service.embed_and_publish(activity)
                    print("EMBED:", activity.id)
                except Exception:
                    logger.exception(
                        "Embedding failed for activity %s",
                        activity.id,
                    )

                    # Keep activity available for retry
                    activity.status = "summarized"

                    await self.session.flush()

                result.processed += 1
                logger.debug("Processed activity #%d successfully", index)
            except Exception:
                logger.exception("Failed processing activity")
                result.failed += 1

        if raw_items:
            source.last_synced_at = utc_now()
        print("ABOUT TO COMMIT")
        await self.session.commit()
        print("COMMIT DONE")
        return result

