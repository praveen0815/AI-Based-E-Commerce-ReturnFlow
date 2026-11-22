"""Dependency probes and the database session boundary."""

from __future__ import annotations

import asyncio

import pytest

from app.api import deps
from app.repositories.base import BaseRepository
from app.services.health import check_database, check_redis


class _Session:
    def __init__(self, error: Exception | None = None, delay: float = 0) -> None:
        self.error = error
        self.delay = delay

    async def execute(self, _statement: object) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Redis:
    def __init__(self, error: Exception | None = None, delay: float = 0) -> None:
        self.error = error
        self.delay = delay

    async def ping(self) -> bool:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return True


class SecretLeak(Exception):
    """Stand-in whose message must never be returned to clients."""


async def test_database_check_succeeds() -> None:
    result = await check_database(lambda: _Session(), timeout=1)
    assert result.status == "up"
    assert result.detail is None


async def test_database_check_reports_the_exception_type_only() -> None:
    session = _Session(error=SecretLeak("password=super-secret"))
    result = await check_database(lambda: session, timeout=1)
    assert result.status == "down"
    assert result.detail == "SecretLeak"


async def test_database_check_times_out() -> None:
    result = await check_database(lambda: _Session(delay=1), timeout=0.01)
    assert result.status == "down"
    assert result.detail == "TimeoutError"


async def test_redis_check_succeeds() -> None:
    result = await check_redis(_Redis(), timeout=1)
    assert result.status == "up"


async def test_redis_check_reports_the_exception_type_only() -> None:
    result = await check_redis(_Redis(error=ConnectionError("redis://secret")), timeout=1)
    assert result.status == "down"
    assert result.detail == "ConnectionError"


async def test_redis_check_times_out() -> None:
    result = await check_redis(_Redis(delay=1), timeout=0.01)
    assert result.status == "down"
    assert result.detail == "TimeoutError"


async def test_get_db_rolls_back_when_the_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.rolled_back = False

        async def rollback(self) -> None:
            self.rolled_back = True

    class Context:
        def __init__(self, session: FakeSession) -> None:
            self.session = session

        async def __aenter__(self) -> FakeSession:
            return self.session

        async def __aexit__(self, *_args: object) -> None:
            return None

    session = FakeSession()
    monkeypatch.setattr(deps, "get_session_factory", lambda: (lambda: Context(session)))

    generator = deps.get_db()
    yielded = await generator.__anext__()
    assert yielded is session
    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))
    assert session.rolled_back is True


def test_repository_keeps_the_request_session() -> None:
    sentinel = object()
    repository = BaseRepository(sentinel)  # type: ignore[arg-type]
    assert repository.session is sentinel
