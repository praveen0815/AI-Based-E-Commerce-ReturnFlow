"""Mock refund and logistics workflow."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers
from tests.commerce_helpers import load_sample_order, setup_customer, setup_owner_store

pytestmark = pytest.mark.usefixtures("isolated_auth")


def _create_return(client: TestClient, owner_token: str, store_id: str, resolution: str = "REFUND") -> str:
    commerce = load_sample_order(client, owner_token, store_id)
    customer = setup_customer(client, owner_token, store_id, "fulfillment")
    order_id = commerce["order_id"]
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], store_id),
    )
    line_id = order.json()["data"]["items"][0]["id"]
    response = client.post(
        "/api/v1/stores/current/returns",
        headers=auth_headers(customer["token"], store_id),
        json={
            "order_id": order_id,
            "reason": "Defective",
            "description": "Item damaged.",
            "requested_resolution": resolution,
            "items": [{"order_item_id": line_id, "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _approve(client: TestClient, token: str, store_id: str, return_id: str) -> None:
    for status in ("UNDER_REVIEW", "APPROVED"):
        response = client.patch(
            f"/api/v1/stores/current/returns/{return_id}/status",
            headers=auth_headers(token, store_id),
            json={"status": status, "note": f"Move to {status}"},
        )
        assert response.status_code == 200, response.text


def _idem() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


def test_happy_path_refund_flow(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-happy")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    _approve(client, setup["token"], setup["store_id"], return_id)

    label = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/label",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert label.status_code == 200, label.text
    assert label.json()["data"]["return_status"] == "LABEL_GENERATED"
    assert label.json()["data"]["shipment"]["tracking_number"]

    transit = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/in-transit",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert transit.status_code == 200
    assert transit.json()["data"]["return_status"] == "RETURN_IN_TRANSIT"

    received = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/received",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert received.status_code == 200
    assert received.json()["data"]["return_status"] == "RECEIVED"

    refund = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/refund",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert refund.status_code == 200
    assert refund.json()["data"]["return_status"] == "REFUND_PENDING"

    finalize = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/refund/finalize",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert finalize.status_code == 200
    assert finalize.json()["data"]["return_status"] == "REFUND_COMPLETED"

    done = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/complete",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert done.status_code == 200
    assert done.json()["data"]["return_status"] == "COMPLETED"

    snap = client.get(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert snap.status_code == 200
    assert len(snap.json()["data"]["notifications"]) >= 4


def test_idempotent_label_request(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-idem")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    _approve(client, setup["token"], setup["store_id"], return_id)
    key = str(uuid.uuid4())
    headers = {**auth_headers(setup["token"], setup["store_id"]), "Idempotency-Key": key}
    first = client.post(f"/api/v1/stores/current/returns/{return_id}/fulfillment/label", headers=headers)
    second = client.post(f"/api/v1/stores/current/returns/{return_id}/fulfillment/label", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["shipment"]["id"] == second.json()["data"]["shipment"]["id"]


def test_mock_refund_failure_and_retry(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-fail")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    _approve(client, setup["token"], setup["store_id"], return_id)
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/label",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/in-transit",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/received",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )

    fail = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/refund",
        headers={**auth_headers(setup["token"], setup["store_id"]), "Idempotency-Key": "fail-refund-run"},
    )
    assert fail.status_code == 200
    assert fail.json()["data"]["refund"]["status"] == "FAILED"

    retry = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/refund",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert retry.status_code == 200
    assert retry.json()["data"]["refund"]["status"] == "PROCESSING"


def test_customer_cannot_request_label(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-cust")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    customer = setup_customer(client, setup["token"], setup["store_id"], "ful-cust2")
    response = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/label",
        headers={**auth_headers(customer["token"], setup["store_id"]), **_idem()},
    )
    assert response.status_code == 403


def test_cancelled_return_blocks_fulfillment(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-cancel")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    cancel = client.post(
        f"/api/v1/stores/current/returns/{return_id}/cancel",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert cancel.status_code == 200
    response = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/label",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert response.status_code == 409


def test_exchange_skips_refund(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-exch")
    return_id = _create_return(client, setup["token"], setup["store_id"], resolution="EXCHANGE")
    _approve(client, setup["token"], setup["store_id"], return_id)
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/label",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/in-transit",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/received",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    bad = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/refund",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert bad.status_code == 409
    good = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/exchange",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert good.status_code == 200
    assert good.json()["data"]["return_status"] == "EXCHANGE_PROCESSING"


def test_in_transit_without_label(client: TestClient) -> None:
    setup = setup_owner_store(client, "ful-nolabel")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    _approve(client, setup["token"], setup["store_id"], return_id)
    response = client.post(
        f"/api/v1/stores/current/returns/{return_id}/fulfillment/shipment/in-transit",
        headers={**auth_headers(setup["token"], setup["store_id"]), **_idem()},
    )
    assert response.status_code == 409