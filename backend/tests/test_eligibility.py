"""Deterministic return eligibility engine."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers, create_store, register
from tests.commerce_helpers import create_customer_order, setup_customer, setup_owner_store

pytestmark = pytest.mark.usefixtures("isolated_auth")


def _evaluate(client: TestClient, token: str, store_id: str, payload: dict) -> dict:
    response = client.post(
        "/api/v1/stores/current/returns/eligibility/evaluate",
        headers=auth_headers(token, store_id),
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_eligible_fulfilled_order(client: TestClient) -> None:
    setup = setup_owner_store(client, "elig-ok")
    customer = setup_customer(client, setup["token"], setup["store_id"], "elig-ok")
    order_id = create_customer_order(setup["store_id"], customer["customer"]["user"]["id"])
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], setup["store_id"]),
    ).json()["data"]
    line_id = order["items"][0]["id"]
    result = _evaluate(
        client,
        customer["token"],
        setup["store_id"],
        {
            "order_id": order_id,
            "reason": "Too small",
            "description": "Shirt does not fit as expected.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": line_id, "quantity": 1, "condition": "NEW"}],
        },
    )
    assert result["decision"] == "ELIGIBLE"
    assert result["decision_code"] == "ELIGIBLE_ALL_RULES_PASSED"


def test_return_window_boundary_expired(client: TestClient) -> None:
    setup = setup_owner_store(client, "elig-window")
    customer = setup_customer(client, setup["token"], setup["store_id"], "elig-window")
    order_id = create_customer_order(setup["store_id"], customer["customer"]["user"]["id"])

    async def _stale_fulfillment() -> None:
        import asyncpg

        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            await conn.execute(
                "UPDATE orders SET fulfillment_date = $1, return_window_days = 30 WHERE id = $2",
                datetime.now(UTC) - timedelta(days=31),
                uuid.UUID(order_id),
            )
        finally:
            await conn.close()

    import asyncio

    asyncio.run(_stale_fulfillment())

    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], setup["store_id"]),
    ).json()["data"]
    result = _evaluate(
        client,
        customer["token"],
        setup["store_id"],
        {
            "order_id": order_id,
            "reason": "Late return",
            "description": "Customer missed the deadline.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
        },
    )
    assert result["decision"] == "INELIGIBLE"
    assert result["decision_code"] == "INELIGIBLE_RETURN_WINDOW_EXPIRED"


def test_final_sale_blocked(client: TestClient) -> None:
    setup = setup_owner_store(client, "elig-final")
    customer = setup_customer(client, setup["token"], setup["store_id"], "elig-final")
    order_id = create_customer_order(setup["store_id"], customer["customer"]["user"]["id"])

    async def _final_sale() -> None:
        import asyncpg

        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            await conn.execute(
                "UPDATE order_items SET item_metadata = '{\"final_sale\": true}'::jsonb WHERE order_id = $1",
                uuid.UUID(order_id),
            )
        finally:
            await conn.close()

    import asyncio

    asyncio.run(_final_sale())
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], setup["store_id"]),
    ).json()["data"]
    result = _evaluate(
        client,
        customer["token"],
        setup["store_id"],
        {
            "order_id": order_id,
            "reason": "Changed mind",
            "description": "No longer needed.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
        },
    )
    assert result["decision"] == "INELIGIBLE"
    assert result["decision_code"] == "INELIGIBLE_FINAL_SALE"


def test_damaged_needs_review(client: TestClient) -> None:
    setup = setup_owner_store(client, "elig-dmg")
    customer = setup_customer(client, setup["token"], setup["store_id"], "elig-dmg")
    order_id = create_customer_order(setup["store_id"], customer["customer"]["user"]["id"])
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], setup["store_id"]),
    ).json()["data"]
    result = _evaluate(
        client,
        customer["token"],
        setup["store_id"],
        {
            "order_id": order_id,
            "reason": "Damaged",
            "description": "Box arrived crushed.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1, "condition": "DAMAGED"}],
        },
    )
    assert result["decision"] == "NEEDS_REVIEW"
    assert result["decision_code"] == "NEEDS_REVIEW_DAMAGED_ITEM"


def test_tenant_isolation(client: TestClient) -> None:
    owner_a = register(client, "elig-a@example.com", "A")
    store_a = create_store(client, owner_a["token"]["access_token"], "Store A")
    owner_b = register(client, "elig-b@example.com", "B")
    store_b = create_store(client, owner_b["token"]["access_token"], "Store B")
    customer = setup_customer(client, owner_a["token"]["access_token"], store_a["id"], "iso")
    order_id = create_customer_order(store_a["id"], customer["customer"]["user"]["id"])
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], store_a["id"]),
    ).json()["data"]
    foreign = client.post(
        "/api/v1/stores/current/returns/eligibility/evaluate",
        headers=auth_headers(owner_b["token"]["access_token"], store_b["id"]),
        json={
            "order_id": order_id,
            "reason": "Test",
            "description": "Cross-tenant attempt.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
        },
    )
    assert foreign.status_code == 200
    assert foreign.json()["data"]["decision"] == "INELIGIBLE"
    assert foreign.json()["data"]["decision_code"] == "INELIGIBLE_ORDER_NOT_FOUND"


def test_ai_explanation_does_not_change_decision(client: TestClient) -> None:
    setup = setup_owner_store(client, "elig-ai")
    customer = setup_customer(client, setup["token"], setup["store_id"], "elig-ai")
    order_id = create_customer_order(setup["store_id"], customer["customer"]["user"]["id"])
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], setup["store_id"]),
    ).json()["data"]
    evaluated = _evaluate(
        client,
        customer["token"],
        setup["store_id"],
        {
            "order_id": order_id,
            "reason": "Fit",
            "description": "Does not fit.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1, "condition": "NEW"}],
            "include_ai_explanation": True,
        },
    )
    assert evaluated["decision"] == "ELIGIBLE"
    assert evaluated["ai_explanation"]
    assert evaluated["ai_model"] == "mock-policy-llm"