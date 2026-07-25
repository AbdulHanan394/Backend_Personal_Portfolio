"""Central exception hierarchy and FastAPI error handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AbdulCoreError(Exception):
    """Base class for domain-aware Abdul Core exceptions."""

    code = "abdul_core_error"
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CollectorError(AbdulCoreError):
    """Raised when an external collector fails."""

    code = "collector_error"
    status_code = 502


class CollectorNotImplementedError(CollectorError):
    """Raised by intentionally stubbed collectors."""

    code = "collector_not_implemented"
    status_code = 501


class AIProcessingError(AbdulCoreError):
    """Raised when AI enrichment fails."""

    code = "ai_processing_error"
    status_code = 502


class EmbeddingError(AbdulCoreError):
    """Raised when embedding or vector storage fails."""

    code = "embedding_error"
    status_code = 502


class NotFoundError(AbdulCoreError):
    """Raised when a requested resource does not exist."""

    code = "not_found"
    status_code = 404


class ValidationError(AbdulCoreError):
    """Raised for domain validation failures."""

    code = "validation_error"
    status_code = 422


class RateLimitedError(AbdulCoreError):
    """Raised when a caller exceeds the configured rate limit."""

    code = "rate_limited"
    status_code = 429


def register_error_handlers(app: FastAPI) -> None:
    """Register consistent JSON error handlers."""

    @app.exception_handler(AbdulCoreError)
    async def handle_abdul_core_error(
        _request: Request, exc: AbdulCoreError
    ) -> JSONResponse:
        headers = {"Retry-After": "60"} if isinstance(exc, RateLimitedError) else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        settings = get_settings()
        logger.exception("unhandled_exception", exc_info=exc)
        message = "Internal server error" if settings.app_env == "production" else str(exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": message}},
        )

