"""Return label, shipment, and refund workflow."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_any_store_permission, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.services.fulfillment.service import (
    complete_return,
    finalize_refund,
    get_fulfillment_snapshot,
    initiate_refund,
    mark_received,
    mark_shipment_in_transit,
    request_return_label,
    start_exchange_fulfillment,
)

router = APIRouter(prefix="/stores/current/returns")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/{return_id}/fulfillment", summary="Fulfillment snapshot")
async def fulfillment_snapshot(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await get_fulfillment_snapshot(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor_id=context.user.id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/label", summary="Request return shipping label")
async def fulfillment_label(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await request_return_label(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/shipment/in-transit", summary="Mark return shipment in transit")
async def fulfillment_in_transit(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await mark_shipment_in_transit(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/shipment/received", summary="Mark return received")
async def fulfillment_received(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await mark_received(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/refund", summary="Initiate mock refund")
async def fulfillment_refund(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await initiate_refund(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/refund/finalize", summary="Finalize mock refund")
async def fulfillment_refund_finalize(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await finalize_refund(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/exchange", summary="Start exchange fulfillment")
async def fulfillment_exchange(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    body = await start_exchange_fulfillment(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        idempotency_key=idempotency_key,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/fulfillment/complete", summary="Close return case")
async def fulfillment_complete(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await complete_return(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))