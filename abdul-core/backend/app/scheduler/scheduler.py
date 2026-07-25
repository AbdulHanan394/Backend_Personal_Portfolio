"""APScheduler setup tied to FastAPI lifespan."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import get_settings
from app.scheduler.jobs import resume_stuck_pipeline, run_source_sync


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the process-local scheduler."""

    settings = get_settings()
    scheduler = AsyncIOScheduler(
        timezone=settings.scheduler_timezone,
        jobstores={"default": SQLAlchemyJobStore(url=settings.database_url_sync)},
    )
    scheduler.add_job(
        run_source_sync,
        CronTrigger.from_crontab(settings.github_sync_cron, timezone=settings.scheduler_timezone),
        args=["github"],
        id="github_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        run_source_sync,
        CronTrigger.from_crontab(settings.x_sync_cron, timezone=settings.scheduler_timezone),
        args=["x"],
        id="x_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        resume_stuck_pipeline,
        IntervalTrigger(minutes=15, timezone=settings.scheduler_timezone),
        id="resume_stuck_pipeline",
        replace_existing=True,
    )
    return scheduler
