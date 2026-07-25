"""Retry utilities for external side effects."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    retryable: tuple[type[Exception], ...] = (TimeoutError, ConnectionError),
) -> T:
    """Retry an async callable with exponential backoff on retryable errors."""

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await func()
        except retryable as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(base_delay * (2**attempt))
    assert last_error is not None
    raise last_error

