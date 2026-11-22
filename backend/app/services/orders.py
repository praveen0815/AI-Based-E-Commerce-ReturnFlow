"""Order reads scoped to store membership."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.order_enums import OrderStatus, PaymentStatus
from app.core.permissions import MemberRole, Permission, has_permission
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.repositories.returns import ReturnRepository
from app.schemas.order import OrderItemPublic, OrderPublic


def return_window_ends(order: Order) -> datetime | None:
    if order.fulfillment_date is None:
        return None
    return order.fulfillment_date + timedelta(days=order.return_window_days)


async def list_orders(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    page: int,
    page_size: int,
    sort: str,
    direction: str,
    status: OrderStatus | None,
    payment_status: PaymentStatus | None,
    q: str | None,
) -> tuple[list[OrderPublic], int]:
    customer_scope: uuid.UUID | None = None
    if has_permission(role, Permission.ORDER_READ):
        customer_scope = None
    elif has_permission(role, Permission.ORDER_READ_OWN):
        customer_scope = actor_id
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    rows, total = await OrderRepository(session).list_in_store(
        store_id,
        customer_user_id=customer_scope,
        page=page,
        page_size=page_size,
        sort=sort if sort in {"order_date", "order_number", "total_amount", "status"} else "order_date",
        direction="asc" if direction == "asc" else "desc",
        status=status,
        payment_status=payment_status,
        q=q,
    )
    returns_repo = ReturnRepository(session)
    items: list[OrderPublic] = []
    for order, email, display_name in rows:
        items.append(await _order_public(session, order, email, display_name, returns_repo, include_items=False))
    return items, total


async def get_order(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
) -> OrderPublic:
    customer_scope: uuid.UUID | None = None
    if has_permission(role, Permission.ORDER_READ):
        customer_scope = None
    elif has_permission(role, Permission.ORDER_READ_OWN):
        customer_scope = actor_id
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    order = await OrderRepository(session).get_in_store(store_id, order_id, customer_user_id=customer_scope)
    if order is None:
        raise AppError("Order not found", code="order_not_found", status_code=404)
    user = order.customer
    return await _order_public(
        session,
        order,
        user.email,
        user.display_name,
        ReturnRepository(session),
        include_items=True,
    )


async def _order_public(
    session: AsyncSession,
    order: Order,
    email: str,
    display_name: str,
    returns_repo: ReturnRepository,
    *,
    include_items: bool,
) -> OrderPublic:
    item_payloads: list[OrderItemPublic] = []
    if include_items:
        for line in order.items:
            returned = await returns_repo.returned_quantity(line.id)
            item_payloads.append(
                OrderItemPublic(
                    id=line.id,
                    product_id=line.product_id,
                    line_name=line.line_name,
                    sku=line.sku,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    item_metadata=line.item_metadata,
                    returnable_quantity=max(0, line.quantity - returned),
                )
            )
    return OrderPublic(
        id=order.id,
        order_number=order.order_number,
        customer_user_id=order.customer_user_id,
        customer_email=email,
        customer_display_name=display_name,
        order_date=order.order_date,
        fulfillment_date=order.fulfillment_date,
        status=order.status,
        payment_status=order.payment_status,
        currency=order.currency,
        total_amount=order.total_amount,
        is_sample=order.is_sample,
        return_window_days=order.return_window_days,
        return_window_ends_at=return_window_ends(order),
        items=item_payloads,
    )