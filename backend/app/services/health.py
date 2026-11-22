"""Dependency probes used by the readiness endpoint."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.schemas.health import DependencyCheck


class _SupportsPing(Protocol):
    def ping(self) -> Awaitable[object]: ...


async def check_database(
    session_factory: async_sessionmaker[AsyncSession] | Callable[[], object],
    timeout: float,
) -> DependencyCheck:
    """Run ``SELECT 1`` and report only the outcome, never the connection string."""

    async def _ping() -> None:
        session_context = session_factory()
        async with session_context as session:  # type: ignore[attr-defined]
            await session.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping(), timeout=timeout)
    except Exception as exc:
        return DependencyCheck(status="down", detail=type(exc).__name__)
    return DependencyCheck(status="up")


async def check_redis(client: _SupportsPing, timeout: float) -> DependencyCheck:
    """Ping Redis and report only the outcome."""

    try:
        await asyncio.wait_for(client.ping(), timeout=timeout)
    except Exception as exc:
        return DependencyCheck(status="down", detail=type(exc).__name__)
    return DependencyCheck(status="up")
