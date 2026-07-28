"""Scheduled job functions."""

from app.database.session import AsyncSessionLocal
from app.repositories.scheduler_log_repo import SchedulerLogRepository
from app.services.sync_service import SyncService
from app.utils.time import utc_now
from sqlalchemy import text

LOCK_KEYS = {
    "github": 120260701,
    "x": 120260702,
    "linkedin": 120260703,
}


async def run_source_sync(source_slug: str) -> None:
    """Run a source sync and record scheduler status."""
    print("\n========== SYNC START ==========")
    print("SOURCE:", source_slug)
    async with AsyncSessionLocal() as session:
        repo = SchedulerLogRepository(session)
        log = await repo.start(f"{source_slug}_sync", utc_now())
        await session.commit()
        lock_key = LOCK_KEYS.get(source_slug, 120260700)
        print("Trying advisory lock...")
        acquired = await session.scalar(text("select pg_try_advisory_lock(:key)"), {"key": lock_key})
        print("Advisory lock result:", acquired)
        if not acquired:
            await repo.finish(
                log,
                finished_at=utc_now(),
                status="success",
                items_processed=0,
                items_failed=0,
                error_message="Skipped because another replica holds the advisory lock.",
            )
            await session.commit()
            return
        try:
            result = await SyncService(session).run(source_slug)
            await repo.finish(
                log,
                finished_at=utc_now(),
                status="success",
                items_processed=result.processed,
                items_failed=result.failed,
            )
        except Exception as exc:
            await repo.finish(
                log,
                finished_at=utc_now(),
                status="failed",
                items_processed=0,
                items_failed=1,
                error_message=f"{type(exc).__name__}: {exc}",
            )
        finally:
            await session.execute(text("select pg_advisory_unlock(:key)"), {"key": lock_key})
        await session.commit()
        print("SyncService.run() FINISHED")


async def resume_stuck_pipeline() -> None:
    """Placeholder for v1 resumable pipeline hardening."""

    async with AsyncSessionLocal() as session:
        repo = SchedulerLogRepository(session)
        log = await repo.start("resume_stuck_pipeline", utc_now())
        await repo.finish(
            log,
            finished_at=utc_now(),
            status="success",
            items_processed=0,
            items_failed=0,
        )
        await session.commit()
