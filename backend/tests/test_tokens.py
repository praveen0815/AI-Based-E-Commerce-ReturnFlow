"""Access token expiry, signature, and logout invalidation."""

from __future__ import annotations

import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token
from tests.auth_helpers import auth_headers, register

pytestmark = pytest.mark.usefixtures("isolated_auth")

SECRET = "returnflow-test-jwt-secret-32chars"


def test_access_token_has_no_store_or_role_claims() -> None:
    user_id = uuid.uuid4()
    token, token_id, expires_in = create_access_token(user_id=user_id, secret=SECRET, ttl_seconds=900)
    payload = decode_access_token(token, SECRET)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == token_id
    assert expires_in == 900
    assert "store_id" not in payload
    assert "role" not in payload


def test_expired_token_is_rejected() -> None:
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "jti": str(uuid.uuid4()), "iat": now - 120, "exp": now - 30},
        SECRET,
        algorithm="HS256",
    )
    from app.core.exceptions import AppError

    with pytest.raises(AppError) as caught:
        decode_access_token(token, SECRET)
    assert caught.value.code == "token_expired"
    assert caught.value.status_code == 401


def test_tampered_token_is_rejected() -> None:
    token, _token_id, _expires_in = create_access_token(
        user_id=uuid.uuid4(),
        secret=SECRET,
        ttl_seconds=900,
    )
    header, body, _signature = token.split(".")
    from app.core.exceptions import AppError

    with pytest.raises(AppError) as caught:
        decode_access_token(f"{header}.{body}.not-a-valid-signature", SECRET)
    assert caught.value.code == "not_authenticated"


def test_expired_token_is_rejected_by_the_api(client: TestClient) -> None:
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "jti": str(uuid.uuid4()), "iat": now - 120, "exp": now - 30},
        SECRET,
        algorithm="HS256",
    )
    response = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"
    assert token not in response.text


def test_logout_invalidates_the_token_before_expiry(client: TestClient) -> None:
    created = register(client, "ada@example.com")
    token = created["token"]["access_token"]
    assert client.get("/api/v1/profile", headers=auth_headers(token)).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=auth_headers(token)).status_code == 200
    again = client.post("/api/v1/auth/logout", headers=auth_headers(token))
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "not_authenticated"
    profile = client.get("/api/v1/profile", headers=auth_headers(token))
    assert profile.status_code == 401
    assert profile.json()["error"]["code"] == "not_authenticated"


def test_short_signing_secret_is_rejected() -> None:
    from app.core.exceptions import AppError

    with pytest.raises(AppError) as caught:
        create_access_token(user_id=uuid.uuid4(), secret="too-short", ttl_seconds=900)
    assert caught.value.code == "auth_not_configured"
