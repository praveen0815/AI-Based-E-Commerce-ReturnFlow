"""Return creation, cancellation, and status changes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.order_enums import OrderStatus
from app.core.permissions import MemberRole, Permission, has_permission
from app.core.return_lifecycle import (
    RequestedResolution,
    ReturnStatus,
    assert_transition,
    can_customer_cancel,
)
from app.models.return_item import ReturnItem
from app.models.return_request import ReturnRequest
from app.models.return_status_history import ReturnStatusHistory
from app.models.user import User
from app.repositories.orders import OrderRepository
from app.repositories.returns import ReturnRepository
from app.schemas.return_request import (
    ReturnCreate,
    ReturnItemPublic,
    ReturnPublic,
    ReturnStatusEventPublic,
    ReturnStatusUpdate,
)
from app.services.audit import record_audit
from app.services.orders import return_window_ends


async def list_returns(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    page: int,
    page_size: int,
    sort: str,
    direction: str,
    status: ReturnStatus | None,
    q: str | None,
    queue: bool,
) -> tuple[list[ReturnPublic], int]:
    if queue and not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    customer_scope: uuid.UUID | None = None
    if has_permission(role, Permission.RETURN_READ):
        customer_scope = None
    elif has_permission(role, Permission.RETURN_READ_OWN):
        customer_scope = actor_id
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    if queue:
        customer_scope = None

    returns, total = await ReturnRepository(session).list_in_store(
        store_id,
        customer_user_id=customer_scope,
        page=page,
        page_size=page_size,
        sort=sort if sort in {"submitted_at", "return_number", "status"} else "submitted_at",
        direction="asc" if direction == "asc" else "desc",
        status=status,
        q=q,
        queue=queue,
    )
    return [_return_public(item, include_internal=has_permission(role, Permission.RETURN_MANAGE)) for item in returns], total


async def get_return(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
) -> ReturnPublic:
    customer_scope: uuid.UUID | None = None
    if has_permission(role, Permission.RETURN_READ):
        customer_scope = None
    elif has_permission(role, Permission.RETURN_READ_OWN):
        customer_scope = actor_id
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    item = await ReturnRepository(session).get_in_store(store_id, return_id, customer_user_id=customer_scope)
    if item is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    return _return_public(item, include_internal=has_permission(role, Permission.RETURN_MANAGE))


async def get_return_history(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
) -> list[ReturnStatusEventPublic]:
    customer_scope: uuid.UUID | None = None
    if has_permission(role, Permission.RETURN_READ):
        customer_scope = None
    elif has_permission(role, Permission.RETURN_READ_OWN):
        customer_scope = actor_id
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    found = await ReturnRepository(session).get_in_store(store_id, return_id, customer_user_id=customer_scope)
    if found is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    rows = await ReturnRepository(session).list_status_history(return_id)
    return [
        ReturnStatusEventPublic(
            id=entry.id,
            from_status=entry.from_status,
            to_status=entry.to_status,
            actor_email=email,
            note=entry.note,
            created_at=entry.created_at,
        )
        for entry, email in rows
    ]


async def create_return(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    payload: ReturnCreate,
    ip_address: str | None,
) -> ReturnPublic:
    if not has_permission(role, Permission.RETURN_CREATE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    order = await OrderRepository(session).get_in_store(store_id, payload.order_id)
    if order is None:
        raise AppError("Order not found", code="order_not_found", status_code=404)
    if order.customer_user_id != actor.id:
        raise AppError("You can only return your own orders", code="forbidden", status_code=403)
    if order.status != OrderStatus.FULFILLED:
        raise AppError("Only fulfilled orders can be returned", code="order_not_returnable", status_code=409)
    window_end = return_window_ends(order)
    if window_end is None or datetime.now(UTC) > window_end:
        raise AppError("The return window for this order has closed", code="return_window_closed", status_code=409)

    order_items = {line.id: line for line in order.items}
    returns_repo = ReturnRepository(session)
    return_lines: list[ReturnItem] = []
    for line in payload.items:
        order_line = order_items.get(line.order_item_id)
        if order_line is None:
            raise AppError("An order line does not belong to this order", code="order_item_invalid", status_code=422)
        already = await returns_repo.returned_quantity(order_line.id)
        available = order_line.quantity - already
        if line.quantity > available:
            raise AppError("The requested quantity exceeds what is still returnable", code="quantity_exceeds_available", status_code=409)
        return_lines.append(ReturnItem(order_item_id=order_line.id, quantity=line.quantity))

    now = datetime.now(UTC)
    request = ReturnRequest(
        store_id=store_id,
        order_id=order.id,
        customer_user_id=actor.id,
        return_number=_return_number(),
        reason=payload.reason,
        description=payload.description,
        requested_resolution=payload.requested_resolution,
        status=ReturnStatus.REQUESTED,
        submitted_at=now,
        return_window_days=order.return_window_days,
        return_window_ends_at=window_end,
    )
    returns_repo.add(request)
    await session.flush()
    for line in return_lines:
        line.return_request_id = request.id
        session.add(line)
    history = ReturnStatusHistory(
        return_request_id=request.id,
        from_status=None,
        to_status=ReturnStatus.REQUESTED,
        actor_user_id=actor.id,
        note="Return requested",
    )
    session.add(history)
    await record_audit(
        session,
        action="return.created",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(request.id),
        ip_address=ip_address,
        details={"return_number": request.return_number, "order_number": order.order_number},
    )
    await session.commit()
    loaded = await ReturnRepository(session).get_in_store(store_id, request.id)
    assert loaded is not None
    return _return_public(loaded, include_internal=False)


async def cancel_return(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    ip_address: str | None,
) -> ReturnPublic:
    request = await ReturnRepository(session).get_in_store(store_id, return_id)
    if request is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)

    staff = has_permission(role, Permission.RETURN_MANAGE)
    if staff:
        assert_transition(request.status, ReturnStatus.CANCELLED)
    elif has_permission(role, Permission.RETURN_CREATE) and request.customer_user_id == actor.id:
        if not can_customer_cancel(request.status):
            raise AppError("This return can no longer be cancelled", code="return_not_cancellable", status_code=409)
        assert_transition(request.status, ReturnStatus.CANCELLED)
    else:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    await _apply_status(session, request, ReturnStatus.CANCELLED, actor, "Return cancelled", ip_address)
    await session.commit()
    loaded = await ReturnRepository(session).get_in_store(store_id, return_id)
    assert loaded is not None
    return _return_public(loaded, include_internal=staff)


async def update_return_status(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    payload: ReturnStatusUpdate,
    ip_address: str | None,
) -> ReturnPublic:
    if not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    request = await ReturnRepository(session).get_in_store(store_id, return_id)
    if request is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    assert_transition(request.status, payload.status)
    if payload.internal_notes is not None:
        request.internal_notes = payload.internal_notes.strip() or None
    if payload.status in {ReturnStatus.APPROVED, ReturnStatus.REJECTED} and request.decision_at is None:
        request.decision_at = datetime.now(UTC)
    await _apply_status(session, request, payload.status, actor, payload.note, ip_address)
    await session.commit()
    loaded = await ReturnRepository(session).get_in_store(store_id, return_id)
    assert loaded is not None
    return _return_public(loaded, include_internal=True)


async def _apply_status(
    session: AsyncSession,
    request: ReturnRequest,
    new_status: ReturnStatus,
    actor: User,
    note: str | None,
    ip_address: str | None,
) -> None:
    previous = request.status
    request.status = new_status
    session.add(
        ReturnStatusHistory(
            return_request_id=request.id,
            from_status=previous,
            to_status=new_status,
            actor_user_id=actor.id,
            note=note,
        )
    )
    await record_audit(
        session,
        action="return.status_changed",
        actor_user_id=actor.id,
        store_id=request.store_id,
        target_type="return",
        target_id=str(request.id),
        ip_address=ip_address,
        details={"from": previous.value, "to": new_status.value},
    )


def _return_number() -> str:
    return f"RET-{uuid.uuid4().hex[:10].upper()}"


def _return_public(request: ReturnRequest, *, include_internal: bool) -> ReturnPublic:
    items = [
        ReturnItemPublic(
            id=line.id,
            order_item_id=line.order_item_id,
            line_name=line.order_item.line_name,
            sku=line.order_item.sku,
            quantity=line.quantity,
        )
        for line in request.items
    ]
    return ReturnPublic(
        id=request.id,
        return_number=request.return_number,
        order_id=request.order_id,
        order_number=request.order.order_number,
        customer_user_id=request.customer_user_id,
        customer_email=request.customer.email,
        reason=request.reason,
        description=request.description,
        requested_resolution=request.requested_resolution,
        status=request.status,
        submitted_at=request.submitted_at,
        decision_at=request.decision_at,
        return_window_days=request.return_window_days,
        return_window_ends_at=request.return_window_ends_at,
        internal_notes=request.internal_notes if include_internal else None,
        items=items,
    )