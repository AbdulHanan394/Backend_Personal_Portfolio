import asyncio

from app.database.session import AsyncSessionLocal
from app.repositories.source_repo import SourceRepository
from app.services.sync_service import SyncService


async def main():
    async with AsyncSessionLocal() as session:
        source = await SourceRepository(session).get_by_slug("github")

        source.last_synced_at = None
        await session.commit()

        result = await SyncService(session).run("github")

        print(result)


if __name__ == "__main__":
    asyncio.run(main())