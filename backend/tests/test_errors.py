"""Standard error envelopes."""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import AppError
from app.main import create_app


def test_unknown_route_uses_the_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/missing")
    body = response.json()
    assert response.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "Not Found"
    assert body["request_id"] == response.headers["x-request-id"]


def test_validation_errors_are_structured() -> None:
    application = create_app()

    class Payload(BaseModel):
        name: str

    @application.post("/api/v1/_test/echo")
    async def echo(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    with TestClient(application) as test_client:
        response = test_client.post("/api/v1/_test/echo", json={})

    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["loc"] == ["body", "name"]
    assert body["request_id"]


def test_application_errors_keep_their_code() -> None:
    application = create_app()

    @application.get("/api/v1/_test/app-error")
    async def fail() -> None:
        raise AppError("Not allowed", code="forbidden", status_code=403)

    with TestClient(application) as test_client:
        response = test_client.get("/api/v1/_test/app-error")

    body = response.json()
    assert response.status_code == 403
    assert body["error"]["code"] == "forbidden"
    assert body["error"]["message"] == "Not allowed"


def test_http_exception_is_wrapped() -> None:
    application = create_app()

    @application.get("/api/v1/_test/http")
    async def fail() -> None:
        raise HTTPException(status_code=409, detail="Conflict")

    with TestClient(application) as test_client:
        response = test_client.get("/api/v1/_test/http")

    assert response.status_code == 409
    assert response.json()["error"] == {"code": "http_error", "message": "Conflict"}


def test_unexpected_errors_hide_the_exception_text() -> None:
    application = create_app()

    @application.get("/api/v1/_test/boom")
    async def boom() -> None:
        raise RuntimeError("password=super-secret")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/v1/_test/boom")

    body = response.json()
    assert response.status_code == 500
    assert body["success"] is False
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert "super-secret" not in response.text
