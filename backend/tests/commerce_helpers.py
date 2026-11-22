"""Commerce API helpers for tests."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.auth_helpers import PASSWORD, auth_headers, create_store, login, register


def setup_owner_store(client: TestClient, label: str) -> dict:
    owner = register(client, f"{label}-owner@example.com", "Owner")
    store = create_store(client, owner["token"]["access_token"], f"Store {label}")
    return {"owner": owner, "store_id": store["id"], "token": owner["token"]["access_token"]}


def setup_customer(client: TestClient, owner_token: str, store_id: str, label: str) -> dict:
    customer = register(client, f"{label}-customer@example.com", "Customer")
    response = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(owner_token, store_id),
        json={"email": customer["user"]["email"], "role": "CUSTOMER"},
    )
    assert response.status_code == 201, response.text
    session = login(client, customer["user"]["email"])
    return {"customer": customer, "token": session["token"]["access_token"]}


def load_sample_order(client: TestClient, owner_token: str, store_id: str) -> dict:
    response = client.post(
        "/api/v1/stores/current/dev/sample-commerce",
        headers=auth_headers(owner_token, store_id),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def create_customer_order(store_id: str, customer_user_id: str) -> str:
    """Insert a fulfilled order for a customer directly in the test database."""

    async def _run() -> str:
        import asyncpg

        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            order_id = uuid.uuid4()
            product_id = uuid.uuid4()
            order_number = f"TST-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now(UTC)
            fulfilled = now - timedelta(days=2)
            await conn.execute(
                """
                INSERT INTO products (id, store_id, name, sku, created_at, updated_at)
                VALUES ($1, $2, 'Test shirt', 'TST-SHIRT', $3, $3)
                """,
                product_id,
                uuid.UUID(store_id),
                now,
            )
            await conn.execute(
                """
                INSERT INTO orders (
                    id, store_id, customer_user_id, order_number, order_date, fulfillment_date,
                    status, payment_status, currency, total_amount, is_sample, return_window_days,
                    created_at, updated_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, 'FULFILLED', 'PAID', 'USD', 49.00, false, 30, $5, $5
                )
                """,
                order_id,
                uuid.UUID(store_id),
                uuid.UUID(customer_user_id),
                order_number,
                fulfilled - timedelta(days=1),
                fulfilled,
            )
            line_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO order_items (
                    id, order_id, product_id, quantity, unit_price, sku, line_name,
                    item_metadata, created_at, updated_at
                )
                VALUES ($1, $2, $3, 2, 24.50, 'TST-SHIRT', 'Test shirt', '{}'::jsonb, $4, $4)
                """,
                line_id,
                order_id,
                product_id,
                now,
            )
        finally:
            await conn.close()
        return str(order_id)

    return asyncio.run(_run())