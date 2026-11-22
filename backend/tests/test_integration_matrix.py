"""Phase 10 integration test matrix — documents suites exercised (mock LLM/RAG by default).

Run full matrix with PostgreSQL + Redis:

    pytest tests/ -m "not live_llm"

Optional:

    RUN_INTEGRATION=1 pytest -m integration
    pytest -m live_llm  # requires GEMINI_API_KEY
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.mock_llm

_SUITE_FILES = [
    "test_auth.py",
    "test_tokens.py",
    "test_permissions.py",
    "test_tenant_isolation.py",
    "test_commerce.py",
    "test_return_lifecycle.py",
    "test_knowledge.py",
    "test_rag.py",
    "test_eligibility.py",
    "test_ai_review.py",
    "test_fulfillment.py",
    "test_analytics.py",
    "test_phase10_security.py",
    "test_config.py",
    "test_errors.py",
    "test_health.py",
    "test_logging.py",
]


def test_documented_test_modules_exist() -> None:
    root = Path(__file__).resolve().parent
    missing = [name for name in _SUITE_FILES if not (root / name).is_file()]
    assert not missing, f"Missing test modules: {missing}"


def test_conftest_uses_mock_providers() -> None:
    import os

    assert os.environ.get("RAG_EMBEDDINGS_PROVIDER") == "mock"
    assert os.environ.get("LLM_PROVIDER") == "mock"