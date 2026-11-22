"""A caller can only see and change stores they belong to."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import PASSWORD, auth_headers, create_store, register

pytestmark = pytest.mark.usefixtures("isolated_auth")


def test_a_store_header_for_another_tenant_is_rejected(client: TestClient) -> None:
    north_user = register(client, "north@example.com", "North Owner")
    south_user = register(client, "south@example.com", "South Owner")
    north = create_store(client, north_user["token"]["access_token"], "Northwind")
    south = create_store(client, south_user["token"]["access_token"], "Southwind")

    denied = client.get(
        "/api/v1/stores/current",
        headers=auth_headers(north_user["token"]["access_token"], south["id"]),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "store_forbidden"
    assert "Southwind" not in denied.text
    assert south["slug"] not in denied.text

    members = client.get(
        "/api/v1/stores/current/members",
        headers=auth_headers(north_user["token"]["access_token"], south["id"]),
    )
    assert members.status_code == 403
    assert "south@example.com" not in members.text

    audit = client.get(
        "/api/v1/stores/current/audit",
        headers=auth_headers(north_user["token"]["access_token"], south["id"]),
    )
    assert audit.status_code == 403

    own = client.get("/api/v1/stores", headers=auth_headers(north_user["token"]["access_token"]))
    assert own.status_code == 200
    names = [item["name"] for item in own.json()["data"]["stores"]]
    assert names == ["Northwind"]
    assert north["id"] != south["id"]


def test_a_membership_from_another_store_cannot_be_changed(client: TestClient) -> None:
    north_user = register(client, "north@example.com", "North Owner")
    south_user = register(client, "south@example.com", "South Owner")
    register(client, "guest@example.com", "Guest User")
    north = create_store(client, north_user["token"]["access_token"], "Northwind")
    south = create_store(client, south_user["token"]["access_token"], "Southwind")
    added = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(south_user["token"]["access_token"], south["id"]),
        json={"email": "guest@example.com", "password": PASSWORD, "role": "CUSTOMER"},
    )
    assert added.status_code == 201, added.text
    foreign_membership = added.json()["data"]["id"]

    change = client.patch(
        f"/api/v1/stores/current/members/{foreign_membership}",
        headers=auth_headers(north_user["token"]["access_token"], north["id"]),
        json={"role": "ADMIN"},
    )
    assert change.status_code == 404
    assert change.json()["error"]["code"] == "membership_not_found"

    remove = client.delete(
        f"/api/v1/stores/current/members/{foreign_membership}",
        headers=auth_headers(north_user["token"]["access_token"], north["id"]),
    )
    assert remove.status_code == 404

    south_members = client.get(
        "/api/v1/stores/current/members",
        headers=auth_headers(south_user["token"]["access_token"], south["id"]),
    )
    roles = {item["email"]: item["role"] for item in south_members.json()["data"]["members"]}
    assert roles["guest@example.com"] == "CUSTOMER"


def test_store_id_in_the_body_does_not_select_the_tenant(client: TestClient) -> None:
    north_user = register(client, "north@example.com", "North Owner")
    south_user = register(client, "south@example.com", "South Owner")
    register(client, "guest@example.com", "Guest User")
    north = create_store(client, north_user["token"]["access_token"], "Northwind")
    south = create_store(client, south_user["token"]["access_token"], "Southwind")

    created = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(north_user["token"]["access_token"], north["id"]),
        json={"email": "guest@example.com", "role": "SUPPORT_AGENT", "store_id": south["id"]},
    )
    assert created.status_code == 201, created.text

    north_members = client.get(
        "/api/v1/stores/current/members",
        headers=auth_headers(north_user["token"]["access_token"], north["id"]),
    ).json()["data"]["members"]
    south_members = client.get(
        "/api/v1/stores/current/members",
        headers=auth_headers(south_user["token"]["access_token"], south["id"]),
    ).json()["data"]["members"]
    assert any(item["email"] == "guest@example.com" for item in north_members)
    assert all(item["email"] != "guest@example.com" for item in south_members)


def test_store_audit_does_not_include_another_stores_events_or_login_events(client: TestClient) -> None:
    north_user = register(client, "north@example.com", "North Owner")
    south_user = register(client, "south@example.com", "South Owner")
    north = create_store(client, north_user["token"]["access_token"], "Northwind")
    south = create_store(client, south_user["token"]["access_token"], "Southwind")
    client.post(
        "/api/v1/auth/login",
        json={"email": "north@example.com", "password": PASSWORD},
    )

    north_audit = client.get(
        "/api/v1/stores/current/audit",
        headers=auth_headers(north_user["token"]["access_token"], north["id"]),
    )
    assert north_audit.status_code == 200
    north_actions = [item["action"] for item in north_audit.json()["data"]["events"]]
    assert "store.created" in north_actions
    assert "auth.login_succeeded" not in north_actions
    assert "Southwind" not in north_audit.text

    missing = client.get(
        "/api/v1/stores/current/audit",
        headers=auth_headers(south_user["token"]["access_token"], str(uuid.uuid4())),
    )
    assert missing.status_code == 403
    assert south["id"] != north["id"]
