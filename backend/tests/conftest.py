"""Shared API test client.

Environment defaults are applied before the application is imported so the
factory sees a test configuration. Auth tests use a separate database and
Redis DB 15 so local development data is left alone.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("DEBUG", "false")
os.environ["JWT_SECRET"] = "returnflow-test-jwt-secret-32chars"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "100"
os.environ["AUTH_RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
_chroma_dir = Path(__file__).resolve().parent / ".chroma_pytest"
_chroma_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("CHROMA_PERSIST_PATH", str(_chroma_dir))
os.environ.setdefault("RAG_EMBEDDINGS_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("RAG_MIN_RELEVANCE_SCORE", "0")


def _test_database_url() -> str:
    url = ""
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        url = "postgresql+asyncpg://returnflow:returnflow_local_dev@localhost:5432/returnflow"
    base, separator, query = url.partition("?")
    head, slash, _name = base.rpartition("/")
    if not head or slash != "/":
        raise RuntimeError("DATABASE_URL is missing a database name")
    rewritten = f"{head}/returnflow_test"
    if separator:
        rewritten = f"{rewritten}?{query}"
    return rewritten


os.environ["DATABASE_URL"] = _test_database_url()

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

get_settings.cache_clear()

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def reset_auth_storage() -> None:
    """Remove auth rows and flush Redis DB 15 only."""

    redis_url = os.environ["REDIS_URL"]
    if not redis_url.rstrip("/").endswith("/15"):
        raise RuntimeError("Refusing to flush Redis outside database 15")

    async def _run() -> None:
        import asyncpg
        import redis.asyncio as aioredis

        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            await conn.execute(
                "TRUNCATE TABLE fulfillment_idempotency, return_notification_events, return_refunds, "
                "return_shipments, return_ai_review_events, return_ai_review_runs, return_eligibility_decisions, "
                "store_return_policy_rules, policy_chat_feedback, "
                "store_knowledge_documents, return_status_history, return_items, "
                "return_requests, order_items, orders, products, audit_logs, store_memberships, "
                "stores, users RESTART IDENTITY CASCADE"
            )
        finally:
            await conn.close()
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            await redis_client.flushdb()
        finally:
            await redis_client.aclose()

    import shutil

    from app.services.rag.chroma_store import reset_client_for_tests

    chroma_path = os.environ.get("CHROMA_PERSIST_PATH", "")
    if chroma_path:
        shutil.rmtree(chroma_path, ignore_errors=True)
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
    reset_client_for_tests()
    asyncio.run(_run())


@pytest.fixture
def isolated_auth(client: TestClient) -> TestClient:
    reset_auth_storage()
    return client
