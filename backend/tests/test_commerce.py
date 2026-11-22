"""Orders, returns, pagination, and authorization."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers, create_store, login, register
from tests.commerce_helpers import (
    create_customer_order,
    load_sample_order,
    setup_customer,
    setup_owner_store,
)

pytestmark = pytest.mark.usefixtures("isolated_auth")


def test_owner_sees_store_orders_and_customer_sees_only_theirs(client: TestClient) -> None:
    ctx = setup_owner_store(client, "north")
    customer = setup_customer(client, ctx["token"], ctx["store_id"], "north")
    order_id = create_customer_order(ctx["store_id"], customer["customer"]["user"]["id"])
    load_sample_order(client, ctx["token"], ctx["store_id"])

    owner_list = client.get("/api/v1/stores/current/orders", headers=auth_headers(ctx["token"], ctx["store_id"]))
    assert owner_list.status_code == 200
    assert owner_list.json()["data"]["total"] == 2

    customer_list = client.get(
        "/api/v1/stores/current/orders/me",
        headers=auth_headers(customer["token"], ctx["store_id"]),
    )
    assert customer_list.status_code == 200
    assert customer_list.json()["data"]["total"] == 1
    assert customer_list.json()["data"]["items"][0]["id"] == order_id

    denied = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
    )
    other_owner_store = register(client, "other-owner@example.com")
    other_store = create_store(client, other_owner_store["token"]["access_token"], "Other")
    cross = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(other_owner_store["token"]["access_token"], other_store["id"]),
    )
    assert cross.status_code == 404
    assert denied.status_code == 200


def test_search_orders_by_number(client: TestClient) -> None:
    ctx = setup_owner_store(client, "search")
    customer = setup_customer(client, ctx["token"], ctx["store_id"], "search")
    create_customer_order(ctx["store_id"], customer["customer"]["user"]["id"])
    listed = client.get(
        "/api/v1/stores/current/orders",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
    ).json()["data"]["items"][0]
    response = client.get(
        f"/api/v1/stores/current/orders/search?q={listed['order_number']}",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


def test_create_cancel_and_review_return(client: TestClient) -> None:
    ctx = setup_owner_store(client, "returns")
    customer = setup_customer(client, ctx["token"], ctx["store_id"], "returns")
    order_id = create_customer_order(ctx["store_id"], customer["customer"]["user"]["id"])
    detail = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], ctx["store_id"]),
    ).json()["data"]
    line_id = detail["items"][0]["id"]

    created = client.post(
        "/api/v1/stores/current/returns",
        headers=auth_headers(customer["token"], ctx["store_id"]),
        json={
            "order_id": order_id,
            "reason": "Wrong size",
            "description": "The shirt is too small.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": line_id, "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    return_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "REQUESTED"

    invalid = client.patch(
        f"/api/v1/stores/current/returns/{return_id}/status",
        headers=auth_headers(customer["token"], ctx["store_id"]),
        json={"status": "APPROVED"},
    )
    assert invalid.status_code == 403

    cancelled = client.post(
        f"/api/v1/stores/current/returns/{return_id}/cancel",
        headers=auth_headers(customer["token"], ctx["store_id"]),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "CANCELLED"

    second = client.post(
        "/api/v1/stores/current/returns",
        headers=auth_headers(customer["token"], ctx["store_id"]),
        json={
            "order_id": order_id,
            "reason": "Damaged",
            "description": "Packaging was torn.",
            "requested_resolution": "EXCHANGE",
            "items": [{"order_item_id": line_id, "quantity": 1}],
        },
    )
    assert second.status_code == 201, second.text
    return_id = second.json()["data"]["id"]

    advanced = client.patch(
        f"/api/v1/stores/current/returns/{return_id}/status",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
        json={"status": "UNDER_REVIEW", "note": "Queued for review"},
    )
    assert advanced.status_code == 200

    bad = client.patch(
        f"/api/v1/stores/current/returns/{return_id}/status",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
        json={"status": "COMPLETED"},
    )
    assert bad.status_code == 409
    assert bad.json()["error"]["code"] == "invalid_return_transition"

    approved = client.patch(
        f"/api/v1/stores/current/returns/{return_id}/status",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200

    history = client.get(
        f"/api/v1/stores/current/returns/{return_id}/history",
        headers=auth_headers(customer["token"], ctx["store_id"]),
    )
    assert history.status_code == 200
    actions = [event["to_status"] for event in history.json()["data"]["events"]]
    assert actions == ["REQUESTED", "UNDER_REVIEW", "APPROVED"]

    queue = client.get(
        "/api/v1/stores/current/returns/queue",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
    )
    assert queue.status_code == 200
    assert queue.json()["data"]["total"] >= 1


def test_sample_order_is_labeled(client: TestClient) -> None:
    ctx = setup_owner_store(client, "sample")
    data = load_sample_order(client, ctx["token"], ctx["store_id"])
    assert data["is_sample"] is True
    orders = client.get(
        "/api/v1/stores/current/orders",
        headers=auth_headers(ctx["token"], ctx["store_id"]),
    ).json()["data"]["items"]
    assert orders[0]["is_sample"] is True