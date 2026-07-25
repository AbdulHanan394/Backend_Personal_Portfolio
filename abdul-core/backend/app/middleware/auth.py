"""Redis-backed API rate limiting middleware."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window-ish minute bucket rate limiter for API routes."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Apply rate limiting to /api/v1 routes."""

        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        settings = get_settings()
        key_identity = request.headers.get("x-api-key") or request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        key = f"rate:{key_identity}:{window}"
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            if count > settings.rate_limit_per_minute:
                return Response(
                    content='{"error":{"code":"rate_limited","message":"Too many requests"}}',
                    media_type="application/json",
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        finally:
            await redis.aclose()
        return await call_next(request)

