"""LangGraph AI return review workflow."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers
from tests.commerce_helpers import load_sample_order, setup_customer, setup_owner_store

pytestmark = pytest.mark.usefixtures("isolated_auth")


def _create_return(client: TestClient, owner_token: str, store_id: str) -> str:
    commerce = load_sample_order(client, owner_token, store_id)
    customer = setup_customer(client, owner_token, store_id, "ai-review")
    order_id = commerce["order_id"]
    order = client.get(
        f"/api/v1/stores/current/orders/{order_id}",
        headers=auth_headers(customer["token"], store_id),
    )
    assert order.status_code == 200, order.text
    line_id = order.json()["data"]["items"][0]["id"]
    response = client.post(
        "/api/v1/stores/current/returns",
        headers=auth_headers(customer["token"], store_id),
        json={
            "order_id": order_id,
            "reason": "Defective",
            "description": "Stitching came undone after one wear.",
            "requested_resolution": "REFUND",
            "items": [{"order_item_id": line_id, "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _wait_review(client: TestClient, token: str, store_id: str, return_id: str, run_id: str) -> dict:
    for _ in range(80):
        response = client.get(
            f"/api/v1/stores/current/returns/{return_id}/ai-review/runs/{run_id}",
            headers=auth_headers(token, store_id),
        )
        assert response.status_code == 200
        status = response.json()["data"]["status"]
        if status in {"AWAITING_HUMAN", "COMPLETED", "FAILED", "TIMED_OUT"}:
            return response.json()["data"]
        time.sleep(0.05)
    raise AssertionError("AI review did not finish")


def test_customer_cannot_start_ai_review(client: TestClient) -> None:
    setup = setup_owner_store(client, "ai-cust")
    customer = setup_customer(client, setup["token"], setup["store_id"], "ai-cust")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    response = client.post(
        f"/api/v1/stores/current/returns/{return_id}/ai-review",
        headers=auth_headers(customer["token"], setup["store_id"]),
    )
    assert response.status_code == 403


def test_ai_review_flow_and_human_resume(client: TestClient) -> None:
    setup = setup_owner_store(client, "ai-flow")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    start = client.post(
        f"/api/v1/stores/current/returns/{return_id}/ai-review",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert start.status_code == 201, start.text
    run_id = start.json()["data"]["id"]
    finished = _wait_review(client, setup["token"], setup["store_id"], return_id, run_id)
    assert finished["status"] == "AWAITING_HUMAN"

    events = client.get(
        f"/api/v1/stores/current/returns/{return_id}/ai-review/runs/{run_id}/events",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert events.status_code == 200
    assert len(events.json()["data"]["events"]) >= 6
    agents = {row["agent"] for row in events.json()["data"]["events"]}
    assert "ELIGIBILITY" in agents
    assert "FINALIZATION" in agents

    output = client.get(
        f"/api/v1/stores/current/returns/{return_id}/ai-review/runs/{run_id}/output",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    body = output.json()["data"]["output"]
    assert body["eligibility"]["locked"] is True
    assert body["finalization"]["requires_human_approval"] is True

    resume = client.post(
        f"/api/v1/stores/current/returns/{return_id}/ai-review/runs/{run_id}/resume",
        headers=auth_headers(setup["token"], setup["store_id"]),
        json={"decision": "ACKNOWLEDGE", "note": "Reviewed in queue"},
    )
    assert resume.status_code == 200
    assert resume.json()["data"]["status"] == "COMPLETED"


def test_tenant_isolation_for_ai_review(client: TestClient) -> None:
    a = setup_owner_store(client, "ai-a")
    b = setup_owner_store(client, "ai-b")
    return_id = _create_return(client, a["token"], a["store_id"])
    start = client.post(
        f"/api/v1/stores/current/returns/{return_id}/ai-review",
        headers=auth_headers(a["token"], a["store_id"]),
    )
    run_id = start.json()["data"]["id"]
    foreign = client.get(
        f"/api/v1/stores/current/returns/{return_id}/ai-review/runs/{run_id}",
        headers=auth_headers(b["token"], b["store_id"]),
    )
    assert foreign.status_code == 404


def test_structured_output_validation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import ValidationError

    from app.schemas.ai_review import IntakeAgentOutput
    from app.services.ai_review import structured_llm

    def bad_json(*_args, **_kwargs):
        raise ValidationError.from_exception_data("IntakeAgentOutput", [])

    monkeypatch.setattr(structured_llm, "_mock_for_agent", bad_json)
    setup = setup_owner_store(client, "ai-bad")
    return_id = _create_return(client, setup["token"], setup["store_id"])
    response = client.post(
        f"/api/v1/stores/current/returns/{return_id}/ai-review",
        headers=auth_headers(setup["token"], setup["store_id"]),
    )
    assert response.status_code == 201
    run_id = response.json()["data"]["id"]
    finished = _wait_review(client, setup["token"], setup["store_id"], return_id, run_id)
    assert finished["status"] in {"AWAITING_HUMAN", "FAILED"}