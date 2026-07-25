"""FastAPI application factory, middleware, routers, and lifespan."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config.settings import get_settings
from app.middleware.auth import RateLimitMiddleware
from app.middleware.error_handler import register_error_handlers
from app.scheduler.scheduler import create_scheduler
from app.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start and stop background scheduler with the ASGI app."""

    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    """Create the FastAPI application."""

    settings = get_settings()
    configure_logging(json_logs=settings.app_env == "production")
    app = FastAPI(title="Abdul Core", debug=settings.app_debug, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    register_error_handlers(app)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
