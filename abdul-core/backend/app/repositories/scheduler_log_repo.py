"""Repository for scheduler log data access."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduler_log import SchedulerLog


class SchedulerLogRepository:
    """Data access for scheduler log rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self, job_name: str, started_at: datetime) -> SchedulerLog:
        """Create a running scheduler log row."""

        log = SchedulerLog(job_name=job_name, started_at=started_at, status="running")
        self.session.add(log)
        await self.session.flush()
        return log

    async def finish(
        self,
        log: SchedulerLog,
        *,
        finished_at: datetime,
        status: str,
        items_processed: int,
        items_failed: int,
        error_message: str | None = None,
    ) -> SchedulerLog:
        """Mark a scheduler log row complete."""

        log.finished_at = finished_at
        log.status = status
        log.items_processed = items_processed
        log.items_failed = items_failed
        log.error_message = error_message
        await self.session.flush()
        return log

    async def recent(self, limit: int = 20) -> list[SchedulerLog]:
        """Return recent scheduler log rows."""

        result = await self.session.scalars(
            select(SchedulerLog).order_by(SchedulerLog.started_at.desc()).limit(limit)
        )
        return list(result)

