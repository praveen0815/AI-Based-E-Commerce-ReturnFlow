"""Live PostgreSQL and Redis checks.

Run after the compose stack is healthy:

    RUN_INTEGRATION=1 pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from app.core.config import get_settings
from app.database.redis import close_redis, get_redis, init_redis
from app.database.session import dispose_engine, get_session_factory, init_engine
from app.services.health import check_database, check_redis

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 to probe live PostgreSQL and Redis",
    ),
]


async def test_postgres_and_redis_accept_connections() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    init_engine(
        settings.database_url,
        echo=False,
        connect_timeout=settings.database_connect_timeout_seconds,
    )
    init_redis(settings.redis_url, connect_timeout=settings.redis_connect_timeout_seconds)
    try:
        database = await check_database(
            get_session_factory(),
            settings.health_check_timeout_seconds,
        )
        redis_status = await check_redis(get_redis(), settings.health_check_timeout_seconds)
    finally:
        await close_redis()
        await dispose_engine()
        get_settings.cache_clear()

    assert database.status == "up", database.detail
    assert redis_status.status == "up", redis_status.detail
