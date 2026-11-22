"""Async Redis client lifecycle."""

from __future__ import annotations

from redis.asyncio import Redis

_client: Redis | None = None


def init_redis(url: str, *, connect_timeout: float = 5.0) -> Redis:
    """Create the process-wide Redis client. The socket opens on first command."""

    global _client
    _client = Redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=connect_timeout,
        socket_timeout=connect_timeout,
        health_check_interval=30,
    )
    return _client


async def close_redis() -> None:
    """Close the Redis connection pool."""

    global _client
    if _client is not None:
        await _client.aclose()
    _client = None


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError("Redis client is not initialized")
    return _client
