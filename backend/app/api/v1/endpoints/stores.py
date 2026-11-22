"""Store and membership routes.

The store is taken from the caller's verified membership, not from a path
or body field supplied by the browser.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_current_user, get_db, get_store_context, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.memberships import MembershipRepository
from app.schemas.audit import AuditPublic
from app.schemas.store import (
    MemberCreate,
    MemberPublic,
    MemberUpdate,
    StoreCreate,
    StorePublic,
    StoreUpdate,
)
from app.services.auth import membership_views
from app.services.stores import add_member, change_member_role, create_store, remove_member, update_store

router = APIRouter(prefix="/stores")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _member_public(membership) -> MemberPublic:
    return MemberPublic(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        display_name=membership.user.display_name,
        role=membership.role,
    )


@router.get("", summary="Stores the current user belongs to")
async def list_stores(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stores = [
        StorePublic(
            id=item["store_id"],
            name=item["store_name"],
            slug=item["store_slug"],
            role=item["role"],
        )
        for item in await membership_views(session, user.id)
    ]
    return JSONResponse(content=success_body({"stores": stores}, _request_id(request)))


@router.post("", status_code=201, summary="Create a store and become its owner")
async def create_store_route(
    payload: StoreCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    store, membership = await create_store(
        session,
        owner=user,
        name=payload.name,
        ip_address=_client_ip(request),
    )
    body = StorePublic(id=store.id, name=store.name, slug=store.slug, role=membership.role)
    return JSONResponse(status_code=201, content=success_body(body, _request_id(request)))


@router.get("/current", summary="The store selected for this request")
async def current_store(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.STORE_READ)),
) -> JSONResponse:
    body = StorePublic(
        id=context.store.id,
        name=context.store.name,
        slug=context.store.slug,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.patch("/current", summary="Rename the current store")
async def update_current_store(
    payload: StoreUpdate,
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.STORE_UPDATE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    store = await update_store(
        session,
        actor=context.user,
        store=context.store,
        name=payload.name,
        ip_address=_client_ip(request),
    )
    body = StorePublic(id=store.id, name=store.name, slug=store.slug, role=context.membership.role)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/current/members", summary="Members of the current store")
async def list_members(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.MEMBERSHIP_READ)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    memberships = await MembershipRepository(session).list_for_store(context.store.id)
    body = {"members": [_member_public(item) for item in memberships]}
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/current/members", status_code=201, summary="Add a member to the current store")
async def create_member(
    payload: MemberCreate,
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.MEMBERSHIP_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    membership = await add_member(
        session,
        actor=context.user,
        actor_role=context.membership.role,
        store_id=context.store.id,
        email=str(payload.email),
        role=payload.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(status_code=201, content=success_body(_member_public(membership), _request_id(request)))


@router.patch("/current/members/{membership_id}", summary="Change a member's role")
async def update_member(
    membership_id: uuid.UUID,
    payload: MemberUpdate,
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.MEMBERSHIP_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    membership = await change_member_role(
        session,
        actor=context.user,
        actor_role=context.membership.role,
        store_id=context.store.id,
        membership_id=membership_id,
        role=payload.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(_member_public(membership), _request_id(request)))


@router.delete("/current/members/{membership_id}", summary="Remove a member")
async def delete_member(
    membership_id: uuid.UUID,
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.MEMBERSHIP_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await remove_member(
        session,
        actor=context.user,
        actor_role=context.membership.role,
        store_id=context.store.id,
        membership_id=membership_id,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body({"status": "removed"}, _request_id(request)))


@router.get("/current/audit", summary="Security events for the current store")
async def list_audit(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.AUDIT_READ)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    rows = await AuditRepository(session).list_for_store(context.store.id)
    events = [
        AuditPublic(
            id=str(entry.id),
            action=entry.action,
            actor_email=email,
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            created_at=entry.created_at,
        )
        for entry, email in rows
    ]
    return JSONResponse(content=success_body({"events": events}, _request_id(request)))
