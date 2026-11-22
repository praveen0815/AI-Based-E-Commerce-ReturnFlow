"""Phase 10 security and consistency checks (API / mock providers)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app import __version__
from tests.auth_helpers import auth_headers, create_store, register

pytestmark = pytest.mark.mock_llm


def test_health_and_version_aligned(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["data"]["version"] == __version__


def test_cors_allows_idempotency_key_header(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "idempotency-key",
        },
    )
    assert response.status_code in {200, 204}
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "idempotency-key" in allowed


@pytest.mark.usefixtures("isolated_auth")
def test_knowledge_rejects_traversal_filename(client: TestClient) -> None:
    setup = register(client, "sec-k@example.com", "Sec Owner")
    store = create_store(client, setup["token"]["access_token"], "Sec Store")
    response = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(setup["token"]["access_token"], store["id"]),
        files={"file": ("../../evil.txt", io.BytesIO(b"# ok\n"), "text/plain")},
        data={"document_type": "RETURN_POLICY"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_filename"


def test_unauthenticated_store_routes_fail_closed(client: TestClient) -> None:
    response = client.get("/api/v1/stores/current/analytics/admin")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"