"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str, *, echo: bool = False, connect_timeout: float = 5.0) -> None:
    """Create the process-wide async engine. Connecting happens on first use."""

    global _engine, _session_factory
    _engine = create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"timeout": connect_timeout},
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def dispose_engine() -> None:
    """Close pooled connections during application shutdown."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialized")
    return _session_factory
