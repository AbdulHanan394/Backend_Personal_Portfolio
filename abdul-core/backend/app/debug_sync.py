import asyncio

from app.database.session import AsyncSessionLocal
from app.collectors.github_collector import GitHubCollector
from app.repositories.source_repo import SourceRepository
from app.services.normalizer import normalize
from app.services.activity_service import ActivityService
from app.services.deduplicator import Deduplicator


async def debug():
    async with AsyncSessionLocal() as session:

        print("=" * 80)
        print("LOADING SOURCE")
        print("=" * 80)

        source = await SourceRepository(session).get_by_slug("github")
        print("Source:", source)
        print("Source ID:", source.id)
        print("Last Synced:", source.last_synced_at)

        print("\n" + "=" * 80)
        print("FETCHING EVENTS")
        print("=" * 80)

        collector = GitHubCollector()

        events = await collector.fetch_raw(None)

        print(f"Fetched {len(events)} events")

        activity_service = ActivityService(session)
        deduplicator = Deduplicator(activity_service.activity_repo)

        for i, raw in enumerate(events, start=1):

            print("\n" + "-" * 80)
            print(f"EVENT #{i}")
            print("-" * 80)

            print("GitHub Event ID :", raw.get("id"))
            print("Type            :", raw.get("type"))

            normalized = normalize("github", raw)

            print("\nNormalized")
            print("External ID :", normalized.external_id)
            print("Title       :", normalized.title)
            print("Type        :", normalized.type)

            duplicate = await deduplicator.is_duplicate(
                source.id,
                normalized.external_id,
            )

            print("\nDuplicate?", duplicate)

            if duplicate:
                print(">>> SKIPPING")
                continue

            activity = await activity_service.insert_normalized(normalized)

            print("\nInserted Activity:")
            print(activity)

        await session.commit()


asyncio.run(debug())