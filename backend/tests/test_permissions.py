"""Role permission map and membership enforcement."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.permissions import ROLE_PERMISSIONS, MemberRole, Permission, has_permission
from app.services.audit import scrub_details
from tests.auth_helpers import PASSWORD, auth_headers, create_store, register

pytestmark = pytest.mark.usefixtures("isolated_auth")


def test_permission_map_matches_the_role_matrix() -> None:
    assert ROLE_PERMISSIONS[MemberRole.OWNER] == frozenset(Permission)
    assert Permission.STORE_UPDATE in ROLE_PERMISSIONS[MemberRole.ADMIN]
    assert Permission.MEMBERSHIP_MANAGE in ROLE_PERMISSIONS[MemberRole.ADMIN]
    assert Permission.AUDIT_READ in ROLE_PERMISSIONS[MemberRole.MANAGER]
    assert Permission.MEMBERSHIP_MANAGE not in ROLE_PERMISSIONS[MemberRole.MANAGER]
    assert Permission.MEMBERSHIP_READ in ROLE_PERMISSIONS[MemberRole.SUPPORT_AGENT]
    assert Permission.AUDIT_READ not in ROLE_PERMISSIONS[MemberRole.SUPPORT_AGENT]
    assert ROLE_PERMISSIONS[MemberRole.CUSTOMER] == frozenset(
        {
            Permission.STORE_READ,
            Permission.ORDER_READ_OWN,
            Permission.RETURN_READ_OWN,
            Permission.RETURN_CREATE,
        }
    )
    assert has_permission(MemberRole.OWNER, Permission.MEMBERSHIP_MANAGE)
    assert not has_permission(MemberRole.CUSTOMER, Permission.AUDIT_READ)


def test_audit_details_drop_secrets() -> None:
    scrubbed = scrub_details(
        {
            "email": "ada@example.com",
            "password": "secret-value",
            "access_token": "header.payload.sig",
            "nested": {"jwt_secret": "nope", "role": "ADMIN"},
        }
    )
    assert scrubbed == {"email": "ada@example.com", "nested": {"role": "ADMIN"}}


def _member(client: TestClient, owner_token: str, store_id: str, email: str, role: str) -> dict:
    response = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(owner_token, store_id),
        json={"email": email, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_customer_support_and_manager_are_limited(client: TestClient) -> None:
    owner = register(client, "owner@example.com", "Store Owner")
    register(client, "customer@example.com", "Casey Customer")
    register(client, "support@example.com", "Sam Support")
    register(client, "manager@example.com", "Morgan Manager")
    store = create_store(client, owner["token"]["access_token"], "Northwind")
    store_id = store["id"]
    owner_token = owner["token"]["access_token"]
    _member(client, owner_token, store_id, "customer@example.com", "CUSTOMER")
    _member(client, owner_token, store_id, "support@example.com", "SUPPORT_AGENT")
    _member(client, owner_token, store_id, "manager@example.com", "MANAGER")

    customer = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": PASSWORD},
    ).json()["data"]["token"]["access_token"]
    support = client.post(
        "/api/v1/auth/login",
        json={"email": "support@example.com", "password": PASSWORD},
    ).json()["data"]["token"]["access_token"]
    manager = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": PASSWORD},
    ).json()["data"]["token"]["access_token"]

    assert client.get("/api/v1/stores/current", headers=auth_headers(customer, store_id)).status_code == 200
    assert client.get("/api/v1/stores/current/members", headers=auth_headers(customer, store_id)).status_code == 403
    assert client.get("/api/v1/stores/current/audit", headers=auth_headers(customer, store_id)).status_code == 403

    assert client.get("/api/v1/stores/current/members", headers=auth_headers(support, store_id)).status_code == 200
    denied_invite = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(support, store_id),
        json={"email": "owner@example.com", "role": "MANAGER"},
    )
    assert denied_invite.status_code == 403
    assert denied_invite.json()["error"]["code"] == "forbidden"
    assert client.get("/api/v1/stores/current/audit", headers=auth_headers(support, store_id)).status_code == 403

    assert client.get("/api/v1/stores/current/audit", headers=auth_headers(manager, store_id)).status_code == 200
    assert (
        client.post(
            "/api/v1/stores/current/members",
            headers=auth_headers(manager, store_id),
            json={"email": "owner@example.com", "role": "ADMIN"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/stores/current",
            headers=auth_headers(manager, store_id),
            json={"name": "Renamed"},
        ).status_code
        == 403
    )


def test_admin_cannot_assign_or_change_an_owner(client: TestClient) -> None:
    owner = register(client, "owner@example.com", "Store Owner")
    register(client, "admin@example.com", "Avery Admin")
    register(client, "new@example.com", "New Person")
    store = create_store(client, owner["token"]["access_token"], "Northwind")
    store_id = store["id"]
    owner_headers = auth_headers(owner["token"]["access_token"], store_id)
    admin_membership = _member(client, owner["token"]["access_token"], store_id, "admin@example.com", "ADMIN")
    admin = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": PASSWORD},
    ).json()["data"]["token"]["access_token"]
    admin_headers = auth_headers(admin, store_id)

    assign_owner = client.post(
        "/api/v1/stores/current/members",
        headers=admin_headers,
        json={"email": "new@example.com", "role": "OWNER"},
    )
    assert assign_owner.status_code == 403
    assert assign_owner.json()["error"]["code"] == "forbidden"

    change_owner = client.patch(
        f"/api/v1/stores/current/members/{store['id']}",
        headers=admin_headers,
        json={"role": "ADMIN"},
    )
    assert change_owner.status_code == 404

    owners = client.get("/api/v1/stores/current/members", headers=owner_headers).json()["data"]["members"]
    owner_membership = next(item for item in owners if item["role"] == "OWNER")
    demote = client.patch(
        f"/api/v1/stores/current/members/{owner_membership['id']}",
        headers=admin_headers,
        json={"role": "ADMIN"},
    )
    assert demote.status_code == 403
    assert admin_membership["role"] == "ADMIN"


def test_the_last_owner_cannot_be_removed_or_demoted(client: TestClient) -> None:
    owner = register(client, "owner@example.com", "Store Owner")
    register(client, "admin@example.com", "Avery Admin")
    store = create_store(client, owner["token"]["access_token"], "Northwind")
    headers = auth_headers(owner["token"]["access_token"], store["id"])
    members = client.get("/api/v1/stores/current/members", headers=headers).json()["data"]["members"]
    owner_membership = members[0]

    demote = client.patch(
        f"/api/v1/stores/current/members/{owner_membership['id']}",
        headers=headers,
        json={"role": "ADMIN"},
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "last_owner"

    remove = client.delete(f"/api/v1/stores/current/members/{owner_membership['id']}", headers=headers)
    assert remove.status_code == 409
    assert remove.json()["error"]["code"] == "last_owner"

    _member(client, owner["token"]["access_token"], store["id"], "admin@example.com", "OWNER")
    demote_ok = client.patch(
        f"/api/v1/stores/current/members/{owner_membership['id']}",
        headers=headers,
        json={"role": "ADMIN"},
    )
    assert demote_ok.status_code == 200
    assert demote_ok.json()["data"]["role"] == "ADMIN"
