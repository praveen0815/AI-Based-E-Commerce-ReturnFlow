"""Fixed-window rate limit for authentication attempts."""

from __future__ import annotations

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.exceptions import AppError


async def enforce_rate_limit(
    redis: Redis,
    *,
    scope: str,
    client_key: str,
    limit: int,
    window_seconds: int,
) -> None:
    key = f"ratelimit:auth:{scope}:{client_key}"
    try:
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, window_seconds)
    except RedisError as exc:
        raise AppError(
            "Authentication is temporarily unavailable",
            code="auth_backend_unavailable",
            status_code=503,
        ) from exc
    if count > limit:
        raise AppError(
            "Too many attempts. Try again later.",
            code="rate_limited",
            status_code=429,
        )
