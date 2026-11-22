"""Registration, login, logout, and account profile."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.auth_helpers import PASSWORD, auth_headers, password_hash_for, register

pytestmark = pytest.mark.usefixtures("isolated_auth")


def test_register_login_me_and_logout(client: TestClient) -> None:
    created = register(client, "ada@example.com", "Ada Owner")
    assert created["user"]["email"] == "ada@example.com"
    assert created["token"]["token_type"] == "bearer"
    assert "password" not in created["user"]
    token = created["token"]["access_token"]

    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["data"]["user"]["display_name"] == "Ada Owner"
    assert me.json()["data"]["memberships"] == []

    logged_out = client.post("/api/v1/auth/logout", headers=auth_headers(token))
    assert logged_out.status_code == 200
    assert logged_out.json()["data"]["status"] == "logged_out"

    reused = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "not_authenticated"


def test_duplicate_email_is_rejected_without_enumeration_of_password(client: TestClient) -> None:
    register(client, "ada@example.com")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "Ada@Example.com", "password": PASSWORD, "display_name": "Ada Owner"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"
    assert PASSWORD not in duplicate.text


def test_unknown_user_and_wrong_password_share_one_error(client: TestClient) -> None:
    register(client, "ada@example.com")
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "not-the-password"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "not-the-password"},
    )
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["error"]["code"] == "invalid_credentials"
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]
    assert "not-the-password" not in unknown.text
    assert "not-the-password" not in wrong.text


def test_password_is_stored_as_an_argon2_hash(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": PASSWORD, "display_name": "Ada Owner"},
    )
    assert response.status_code == 201
    stored = password_hash_for("ada@example.com")
    assert stored.startswith("$argon2")
    assert PASSWORD not in stored
    assert PASSWORD not in response.text
    assert "password_hash" not in response.text


def test_short_password_is_rejected_without_echoing_it(client: TestClient) -> None:
    secret = "short-pass"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": secret, "display_name": "Ada Owner"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert secret not in response.text
    assert "Traceback" not in response.text


def test_login_is_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_RATE_LIMIT_ATTEMPTS", "2")
    get_settings.cache_clear()
    try:
        payload = {"email": "ada@example.com", "password": "not-the-password"}
        first = client.post("/api/v1/auth/login", json=payload)
        second = client.post("/api/v1/auth/login", json=payload)
        third = client.post("/api/v1/auth/login", json=payload)
        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "rate_limited"
    finally:
        monkeypatch.setenv("AUTH_RATE_LIMIT_ATTEMPTS", "100")
        get_settings.cache_clear()


def test_profile_updates_the_display_name(client: TestClient) -> None:
    created = register(client, "ada@example.com", "Ada Owner")
    token = created["token"]["access_token"]
    updated = client.patch(
        "/api/v1/profile",
        headers=auth_headers(token),
        json={"display_name": "Ada Lovelace"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["display_name"] == "Ada Lovelace"
    assert updated.json()["data"]["email"] == "ada@example.com"

    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.json()["data"]["user"]["display_name"] == "Ada Lovelace"


def test_auth_logs_do_not_include_the_password_or_token(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": PASSWORD, "display_name": "Ada Owner"},
    )
    token = response.json()["data"]["token"]["access_token"]
    assert PASSWORD not in caplog.text
    assert token not in caplog.text


def test_missing_token_uses_the_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert "Traceback" not in response.text
