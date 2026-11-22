"""Store analytics and authorization."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers
from tests.commerce_helpers import load_sample_order, setup_customer, setup_owner_store

pytestmark = pytest.mark.usefixtures("isolated_auth")


def _create_return(client: TestClient, owner_token: str, store_id: str) -> None:
    commerce = load_sample_order(client, owner_token, store_id)
    customer = setup_customer(client, owner_token, store_id, "analytics")
    order = client.get(
        f"/api/v1/stores/current/orders/{commerce['order_id']}",
        headers=auth_headers(customer["token"], store_id),
    )
    line_id = order.json()["data"]["items"][0]["id"]
    client.post(
        "/api/v1/stores/current/returns",
        headers=auth_headers(customer["token"], store_id),
        json={
            "order_id": commerce["order_id"],
            "reason": "Defective",
            "description": "Test return for analytics.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": line_id, "quantity": 1}],
        },
    )


def test_admin_analytics_counts(client: TestClient) -> None:
    setup = setup_owner_store(client, "an-admin")
    _create_return(client, setup["token"], setup["store_id"])
    response = client.get(
        "/api/v1/stores/current/analytics/admin",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["kpis"]["total_orders"] >= 1
    assert data["kpis"]["total_return_requests"] >= 1
    assert len(data["return_status_distribution"]) >= 1


def test_customer_analytics_and_staff_forbidden(client: TestClient) -> None:
    setup = setup_owner_store(client, "an-cust")
    customer = setup_customer(client, setup["token"], setup["store_id"], "an-cust2")
    _create_return(client, setup["token"], setup["store_id"])
    me = client.get(
        "/api/v1/stores/current/analytics/me",
        headers=auth_headers(customer["token"], setup["store_id"]),
    )
    assert me.status_code == 200, me.text
    assert me.json()["data"]["kpis"]["active_returns"] >= 1

    blocked = client.get(
        "/api/v1/stores/current/analytics/me",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert blocked.status_code == 403


def test_customer_cannot_read_admin_analytics(client: TestClient) -> None:
    setup = setup_owner_store(client, "an-auth")
    customer = setup_customer(client, setup["token"], setup["store_id"], "an-auth2")
    response = client.get(
        "/api/v1/stores/current/analytics/admin",
        headers=auth_headers(customer["token"], setup["store_id"]),
    )
    assert response.status_code == 403