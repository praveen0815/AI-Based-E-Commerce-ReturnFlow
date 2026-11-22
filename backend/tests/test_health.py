"""Liveness, readiness, correlation ids, and CORS."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.schemas.health import DependencyCheck


def test_root_uses_the_success_envelope(client: TestClient) -> None:
    response = client.get("/")
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["service"] == "ReturnFlow"
    assert body["data"]["health"] == "/api/v1/health"
    assert body["request_id"]
    assert response.headers["x-request-id"] == body["request_id"]


def test_health_is_a_liveness_probe(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "ReturnFlow"
    assert body["data"]["environment"] == get_settings().app_env
    assert body["data"]["version"]
    assert "postgresql" not in response.text
    assert "change-me" not in response.text


def test_request_id_is_preserved_when_it_is_safe(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
    assert response.headers["x-request-id"] == "req-123"
    assert response.json()["request_id"] == "req-123"


def test_unsafe_request_id_characters_are_removed(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "bad id<script>"})
    assert response.headers["x-request-id"] == "badidscript"
    assert "<" not in response.headers["x-request-id"]


def test_ready_returns_200_when_dependencies_are_up(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def database_up(*_args: object, **_kwargs: object) -> DependencyCheck:
        return DependencyCheck(status="up")

    async def redis_up(*_args: object, **_kwargs: object) -> DependencyCheck:
        return DependencyCheck(status="up")

    monkeypatch.setattr("app.api.v1.endpoints.health.check_database", database_up)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis", redis_up)

    response = client.get("/api/v1/ready")
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["status"] == "ready"
    assert body["data"]["checks"]["database"]["status"] == "up"
    assert body["data"]["checks"]["redis"]["status"] == "up"


def test_ready_returns_503_without_connection_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def database_down(*_args: object, **_kwargs: object) -> DependencyCheck:
        return DependencyCheck(status="down", detail="OperationalError")

    async def redis_up(*_args: object, **_kwargs: object) -> DependencyCheck:
        return DependencyCheck(status="up")

    monkeypatch.setattr("app.api.v1.endpoints.health.check_database", database_down)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis", redis_up)

    response = client.get("/api/v1/ready")
    body = response.json()
    assert response.status_code == 503
    assert body["success"] is False
    assert body["error"]["code"] == "not_ready"
    assert body["error"]["details"]["checks"]["database"]["detail"] == "OperationalError"
    assert "postgresql+asyncpg" not in response.text


def test_cors_allows_a_configured_origin(client: TestClient) -> None:
    origin = get_settings().cors_origin_list[0]
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID, X-Store-ID",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-request-id" in allowed_headers
    assert "x-store-id" in allowed_headers


def test_cors_does_not_reflect_an_unknown_origin(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_openapi_lists_versioned_health_routes(client: TestClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/ready" in paths


def test_access_log_omits_the_query_string(client: TestClient) -> None:
    records: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    handler = ListHandler()
    logger = logging.getLogger("returnflow.access")
    logger.addHandler(handler)
    try:
        response = client.get("/api/v1/health", params={"token": "secret-value"})
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 200
    text = "\n".join(records)
    assert "/api/v1/health" in text
    assert "secret-value" not in text
