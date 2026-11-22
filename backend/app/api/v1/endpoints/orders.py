"""Order listing and detail for the current store."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_any_store_permission
from app.core.order_enums import OrderStatus, PaymentStatus
from app.core.permissions import Permission
from app.core.responses import success_body
from app.schemas.order import OrderPublic
from app.schemas.pagination import Paginated
from app.services.orders import get_order, list_orders

router = APIRouter(prefix="/stores/current/orders")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("", summary="List orders for the current store")
async def list_store_orders(
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.ORDER_READ, Permission.ORDER_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("order_date"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
) -> JSONResponse:
    items, total = await list_orders(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        page=page,
        page_size=page_size,
        sort=sort,
        direction=direction,
        status=status,
        payment_status=payment_status,
        q=q,
    )
    body = Paginated[OrderPublic](items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/search", summary="Search orders")
async def search_orders(
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.ORDER_READ, Permission.ORDER_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=120),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    items, total = await list_orders(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        page=page,
        page_size=page_size,
        sort="order_date",
        direction="desc",
        status=None,
        payment_status=None,
        q=q,
    )
    body = Paginated[OrderPublic](items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/me", summary="Customer order history in the current store")
async def my_orders(
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.ORDER_READ, Permission.ORDER_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    items, total = await list_orders(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        page=page,
        page_size=page_size,
        sort="order_date",
        direction="desc",
        status=None,
        payment_status=None,
        q=None,
    )
    body = Paginated[OrderPublic](items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/{order_id}", summary="Order detail")
async def order_detail(
    order_id: uuid.UUID,
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.ORDER_READ, Permission.ORDER_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await get_order(
        session,
        store_id=context.store.id,
        order_id=order_id,
        actor_id=context.user.id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))