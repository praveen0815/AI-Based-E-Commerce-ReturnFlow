"""Helpers for authentication API tests."""

from __future__ import annotations

import asyncio
import os

from fastapi.testclient import TestClient

PASSWORD = "correct-horse-1"


def auth_headers(token: str, store_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if store_id is not None:
        headers["X-Store-ID"] = store_id
    return headers


def register(client: TestClient, email: str, display_name: str = "Ada Owner") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_store(client: TestClient, token: str, name: str) -> dict:
    response = client.post(
        "/api/v1/stores",
        headers=auth_headers(token),
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def password_hash_for(email: str) -> str:
    async def _fetch() -> str:
        import asyncpg

        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            value = await conn.fetchval("SELECT password_hash FROM users WHERE email = $1", email)
        finally:
            await conn.close()
        assert isinstance(value, str)
        return value

    return asyncio.run(_fetch())
