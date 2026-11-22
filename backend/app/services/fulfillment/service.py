"""Return label and refund logistics (mock providers only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.fulfillment_enums import NotificationEventType, RefundProviderStatus, ShipmentProviderStatus
from app.core.permissions import MemberRole, Permission, has_permission
from app.core.return_lifecycle import RequestedResolution, ReturnStatus, assert_transition
from app.models.return_fulfillment import FulfillmentIdempotency, ReturnNotificationEvent, ReturnRefund, ReturnShipment
from app.models.return_request import ReturnRequest
from app.models.return_status_history import ReturnStatusHistory
from app.models.user import User
from app.providers.logistics.factory import get_logistics_provider
from app.providers.refund.factory import get_refund_provider
from app.repositories.fulfillment import FulfillmentRepository
from app.repositories.returns import ReturnRepository
from app.schemas.fulfillment import (
    FulfillmentActionResult,
    FulfillmentSnapshot,
    FulfillmentTimelineStep,
    NotificationPublic,
    RefundPublic,
    ShipmentPublic,
)
from app.services.audit import record_audit

_WORKFLOW_STEPS: list[tuple[str, str, set[ReturnStatus]]] = [
    ("approved", "Approved", {ReturnStatus.APPROVED, ReturnStatus.LABEL_PENDING, ReturnStatus.LABEL_GENERATED, ReturnStatus.RETURN_IN_TRANSIT, ReturnStatus.RECEIVED, ReturnStatus.REFUND_PENDING, ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ("label", "Return label", {ReturnStatus.LABEL_GENERATED, ReturnStatus.RETURN_IN_TRANSIT, ReturnStatus.RECEIVED, ReturnStatus.REFUND_PENDING, ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ("transit", "In transit", {ReturnStatus.RETURN_IN_TRANSIT, ReturnStatus.RECEIVED, ReturnStatus.REFUND_PENDING, ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ("received", "Received", {ReturnStatus.RECEIVED, ReturnStatus.REFUND_PENDING, ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ("refund_pending", "Refund processing", {ReturnStatus.REFUND_PENDING, ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ("refund_done", "Refund completed", {ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
]

_TERMINAL_BLOCK = frozenset({ReturnStatus.CANCELLED, ReturnStatus.REJECTED, ReturnStatus.COMPLETED})


async def get_fulfillment_snapshot(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
) -> FulfillmentSnapshot:
    request = await _load_return(session, store_id, return_id, actor_id, role, read_only=True)
    repo = FulfillmentRepository(session)
    shipment = await repo.latest_shipment(return_id)
    refund = await repo.latest_refund(return_id)
    notifications = await repo.list_notifications(return_id)
    return FulfillmentSnapshot(
        return_id=return_id,
        return_status=request.status,
        shipment=_shipment_public(shipment) if shipment else None,
        refund=_refund_public(refund) if refund else None,
        notifications=[_notification_public(n) for n in notifications],
        timeline=_build_timeline(request, shipment, refund),
    )


async def request_return_label(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "request_label")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)

    repo = FulfillmentRepository(session)
    existing = await repo.shipment_by_idempotency(store_id, idempotency_key)
    if existing:
        body = _action_result(request, existing, await repo.latest_refund(return_id))
        await _store_idempotency(session, store_id, idempotency_key, "request_label", body)
        await session.commit()
        return body

    ready_shipment = await repo.latest_shipment(return_id)
    if ready_shipment and ready_shipment.status == ShipmentProviderStatus.LABEL_READY:
        raise AppError(
            "A return label already exists for this return",
            code="label_already_exists",
            status_code=409,
        )

    if request.status == ReturnStatus.APPROVED:
        await _transition(session, request, ReturnStatus.LABEL_PENDING, actor, "Return label requested", ip_address)
    elif request.status != ReturnStatus.LABEL_PENDING:
        raise AppError(
            f"Return must be approved to request a label (current: {request.status.value})",
            code="invalid_return_transition",
            status_code=409,
        )

    logistics = get_logistics_provider()
    label = logistics.request_label(return_ref=request.return_number, idempotency_key=idempotency_key)

    if label.status == "FAILED":
        shipment = ReturnShipment(
            store_id=store_id,
            return_request_id=return_id,
            status=ShipmentProviderStatus.FAILED,
            carrier=label.carrier,
            tracking_number=label.tracking_number,
            label_url=label.label_url,
            provider_ref=label.provider_ref,
            idempotency_key=idempotency_key,
            failure_reason=label.failure_reason,
        )
        repo.add_shipment(shipment)
        await record_audit(
            session,
            action="fulfillment.label_failed",
            actor_user_id=actor.id,
            store_id=store_id,
            target_type="return",
            target_id=str(return_id),
            ip_address=ip_address,
            details={"provider_ref": label.provider_ref, "reason": label.failure_reason},
        )
        body = FulfillmentActionResult(
            return_status=request.status,
            shipment=_shipment_public(shipment),
            message=label.failure_reason,
        )
        await _store_idempotency(session, store_id, idempotency_key, "request_label", body)
        await session.commit()
        return body

    shipment = ReturnShipment(
        store_id=store_id,
        return_request_id=return_id,
        status=ShipmentProviderStatus.LABEL_READY,
        carrier=label.carrier,
        tracking_number=label.tracking_number,
        label_url=label.label_url,
        provider_ref=label.provider_ref,
        idempotency_key=idempotency_key,
        failure_reason=None,
    )
    repo.add_shipment(shipment)
    await _transition(session, request, ReturnStatus.LABEL_GENERATED, actor, "Return label generated", ip_address)
    await _notify(
        session,
        repo,
        store_id,
        return_id,
        request.customer.email,
        NotificationEventType.RETURN_LABEL_READY,
        f"Return label for {request.return_number}",
        f"Your return label is ready. Tracking: {label.tracking_number}",
    )
    await record_audit(
        session,
        action="fulfillment.label_generated",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={"tracking": label.tracking_number, "carrier": label.carrier},
    )
    body = _action_result(request, shipment, None)
    await _store_idempotency(session, store_id, idempotency_key, "request_label", body)
    await session.commit()
    return body


async def mark_shipment_in_transit(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "mark_in_transit")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    shipment = await FulfillmentRepository(session).latest_shipment(return_id)
    if shipment is None or shipment.status != ShipmentProviderStatus.LABEL_READY:
        raise AppError("Return label is missing or not ready", code="missing_return_label", status_code=409)

    assert_transition(request.status, ReturnStatus.RETURN_IN_TRANSIT)
    await _transition(session, request, ReturnStatus.RETURN_IN_TRANSIT, actor, "Return shipment in transit", ip_address)
    shipment.status = ShipmentProviderStatus.IN_TRANSIT
    repo = FulfillmentRepository(session)
    await _notify(
        session,
        repo,
        store_id,
        return_id,
        request.customer.email,
        NotificationEventType.RETURN_IN_TRANSIT,
        f"Return {request.return_number} is on the way",
        f"Carrier {shipment.carrier} tracking {shipment.tracking_number}",
    )
    await record_audit(
        session,
        action="fulfillment.in_transit",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={"tracking": shipment.tracking_number},
    )
    body = _action_result(request, shipment, await repo.latest_refund(return_id))
    await _store_idempotency(session, store_id, idempotency_key, "mark_in_transit", body)
    await session.commit()
    return body


async def mark_received(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "mark_received")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    repo = FulfillmentRepository(session)
    shipment = await repo.latest_shipment(return_id)
    assert_transition(request.status, ReturnStatus.RECEIVED)
    await _transition(session, request, ReturnStatus.RECEIVED, actor, "Return received at warehouse", ip_address)
    if shipment:
        shipment.status = ShipmentProviderStatus.DELIVERED
    await _notify(
        session,
        repo,
        store_id,
        return_id,
        request.customer.email,
        NotificationEventType.RETURN_RECEIVED,
        f"Return {request.return_number} received",
        "We received your return and will process your resolution shortly.",
    )
    await record_audit(
        session,
        action="fulfillment.received",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={},
    )
    body = _action_result(request, shipment, await repo.latest_refund(return_id))
    await _store_idempotency(session, store_id, idempotency_key, "mark_received", body)
    await session.commit()
    return body


async def initiate_refund(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "initiate_refund")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    if request.requested_resolution == RequestedResolution.EXCHANGE:
        raise AppError(
            "This return requested an exchange; use the exchange workflow instead",
            code="exchange_not_refund",
            status_code=409,
        )
    if request.status not in {ReturnStatus.RECEIVED, ReturnStatus.REFUND_PENDING}:
        raise AppError(
            "Refund can only start after the return is received",
            code="invalid_return_transition",
            status_code=409,
        )

    repo = FulfillmentRepository(session)
    prior = await repo.refund_by_idempotency(store_id, idempotency_key)
    if prior:
        body = _action_result(request, await repo.latest_shipment(return_id), prior)
        await _store_idempotency(session, store_id, idempotency_key, "initiate_refund", body)
        await session.commit()
        return body

    amount, currency = _refund_amount(request)
    refund_provider = get_refund_provider()
    eligibility = refund_provider.check_eligibility(
        amount=amount, currency=currency, order_ref=request.order.order_number
    )
    if not eligibility.eligible:
        refund = ReturnRefund(
            store_id=store_id,
            return_request_id=return_id,
            status=RefundProviderStatus.INELIGIBLE,
            amount=amount,
            currency=currency,
            provider_ref="n/a",
            idempotency_key=idempotency_key,
            failure_reason=eligibility.reason,
        )
        repo.add_refund(refund)
        body = FulfillmentActionResult(
            return_status=request.status,
            refund=_refund_public(refund),
            message=eligibility.reason,
        )
        await _store_idempotency(session, store_id, idempotency_key, "initiate_refund", body)
        await session.commit()
        return body

    if request.status == ReturnStatus.RECEIVED:
        assert_transition(request.status, ReturnStatus.REFUND_PENDING)
        await _transition(session, request, ReturnStatus.REFUND_PENDING, actor, "Refund initiated", ip_address)

    initiated = refund_provider.initiate_refund(
        amount=amount,
        currency=currency,
        order_ref=request.order.order_number,
        idempotency_key=idempotency_key,
    )
    status = RefundProviderStatus.FAILED if initiated.status == "FAILED" else RefundProviderStatus.PROCESSING
    refund = ReturnRefund(
        store_id=store_id,
        return_request_id=return_id,
        status=status,
        amount=amount,
        currency=currency,
        provider_ref=initiated.provider_ref,
        idempotency_key=idempotency_key,
        failure_reason=initiated.failure_reason,
    )
    repo.add_refund(refund)
    event_type = NotificationEventType.REFUND_FAILED if status == RefundProviderStatus.FAILED else NotificationEventType.REFUND_INITIATED
    subject = f"Refund {'failed' if status == RefundProviderStatus.FAILED else 'started'} for {request.return_number}"
    preview = initiated.failure_reason or f"Refund of {amount} {currency} is processing."
    await _notify(session, repo, store_id, return_id, request.customer.email, event_type, subject, preview)
    await record_audit(
        session,
        action="fulfillment.refund_initiated" if status != RefundProviderStatus.FAILED else "fulfillment.refund_failed",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={"amount": str(amount), "provider_ref": initiated.provider_ref, "status": status.value},
    )
    body = _action_result(request, await repo.latest_shipment(return_id), refund, message=initiated.failure_reason)
    await _store_idempotency(session, store_id, idempotency_key, "initiate_refund", body)
    await session.commit()
    return body


async def finalize_refund(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    """Poll mock provider and complete refund when processing succeeds."""
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "finalize_refund")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    repo = FulfillmentRepository(session)
    refund = await repo.latest_refund(return_id)
    if refund is None or refund.status not in {RefundProviderStatus.PROCESSING, RefundProviderStatus.PENDING}:
        raise AppError("No refund is ready to finalize", code="refund_not_ready", status_code=409)

    provider_status = get_refund_provider().get_status(refund.provider_ref)
    if provider_status == "FAILED":
        refund.status = RefundProviderStatus.FAILED
        refund.failure_reason = refund.failure_reason or "Provider reported failure"
        await _notify(
            session,
            repo,
            store_id,
            return_id,
            request.customer.email,
            NotificationEventType.REFUND_FAILED,
            f"Refund failed for {request.return_number}",
            refund.failure_reason,
        )
        body = _action_result(request, await repo.latest_shipment(return_id), refund)
        await _store_idempotency(session, store_id, idempotency_key, "finalize_refund", body)
        await session.commit()
        return body

    refund.status = RefundProviderStatus.COMPLETED
    if request.status == ReturnStatus.REFUND_PENDING:
        assert_transition(request.status, ReturnStatus.REFUND_COMPLETED)
        await _transition(session, request, ReturnStatus.REFUND_COMPLETED, actor, "Refund completed", ip_address)
    await _notify(
        session,
        repo,
        store_id,
        return_id,
        request.customer.email,
        NotificationEventType.REFUND_COMPLETED,
        f"Refund completed for {request.return_number}",
        f"Your refund of {refund.amount} {refund.currency} has been issued (mock).",
    )
    await record_audit(
        session,
        action="fulfillment.refund_completed",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={"provider_ref": refund.provider_ref},
    )
    body = _action_result(request, await repo.latest_shipment(return_id), refund)
    await _store_idempotency(session, store_id, idempotency_key, "finalize_refund", body)
    await session.commit()
    return body


async def start_exchange_fulfillment(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    idempotency_key: str,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise AppError("Idempotency-Key header is required", code="idempotency_required", status_code=422)

    cached = await _cached_response(session, store_id, idempotency_key, "start_exchange")
    if cached is not None:
        return FulfillmentActionResult.model_validate(cached)

    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    if request.requested_resolution != RequestedResolution.EXCHANGE:
        raise AppError("Return did not request an exchange", code="not_exchange_request", status_code=409)
    assert_transition(request.status, ReturnStatus.EXCHANGE_PROCESSING)
    await _transition(session, request, ReturnStatus.EXCHANGE_PROCESSING, actor, "Exchange fulfillment started", ip_address)
    repo = FulfillmentRepository(session)
    await record_audit(
        session,
        action="fulfillment.exchange_started",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={},
    )
    body = _action_result(request, await repo.latest_shipment(return_id), None, message="Exchange processing (mock)")
    await _store_idempotency(session, store_id, idempotency_key, "start_exchange", body)
    await session.commit()
    return body


async def complete_return(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    ip_address: str | None,
) -> FulfillmentActionResult:
    _require_manage(role)
    request = await _load_return(session, store_id, return_id, actor.id, role, read_only=False)
    _assert_active_return(request)
    if request.status not in {ReturnStatus.REFUND_COMPLETED, ReturnStatus.EXCHANGE_PROCESSING, ReturnStatus.REFUND_PROCESSING}:
        raise AppError(
            "Return must finish refund or exchange before completion",
            code="invalid_return_transition",
            status_code=409,
        )
    assert_transition(request.status, ReturnStatus.COMPLETED)
    await _transition(session, request, ReturnStatus.COMPLETED, actor, "Return case closed", ip_address)
    repo = FulfillmentRepository(session)
    await record_audit(
        session,
        action="fulfillment.return_completed",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="return",
        target_id=str(return_id),
        ip_address=ip_address,
        details={},
    )
    await session.commit()
    return _action_result(request, await repo.latest_shipment(return_id), await repo.latest_refund(return_id))


def _require_manage(role: MemberRole) -> None:
    if not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)


async def _load_return(
    session: AsyncSession,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    *,
    read_only: bool,
) -> ReturnRequest:
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
    _ = read_only
    return item


def _assert_active_return(request: ReturnRequest) -> None:
    if request.status in _TERMINAL_BLOCK:
        raise AppError(
            f"Return is {request.status.value} and cannot be updated",
            code="return_terminal",
            status_code=409,
        )


async def _transition(
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


async def _notify(
    session: AsyncSession,
    repo: FulfillmentRepository,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    email: str,
    event_type: NotificationEventType,
    subject: str,
    body_preview: str,
) -> None:
    repo.add_notification(
        ReturnNotificationEvent(
            store_id=store_id,
            return_request_id=return_id,
            event_type=event_type.value,
            recipient_email=email,
            subject=subject,
            body_preview=body_preview[:500],
            mock_delivered=True,
        )
    )


async def _cached_response(
    session: AsyncSession, store_id: uuid.UUID, idempotency_key: str, operation: str
) -> dict[str, Any] | None:
    row = await FulfillmentRepository(session).get_idempotency(store_id, idempotency_key)
    if row is None:
        return None
    if row.operation != operation:
        raise AppError(
            "Idempotency key was already used for a different operation",
            code="idempotency_conflict",
            status_code=409,
        )
    return row.response_body


async def _store_idempotency(
    session: AsyncSession,
    store_id: uuid.UUID,
    idempotency_key: str,
    operation: str,
    body: FulfillmentActionResult,
) -> None:
    FulfillmentRepository(session).save_idempotency(
        FulfillmentIdempotency(
            store_id=store_id,
            idempotency_key=idempotency_key,
            operation=operation,
            response_body=body.model_dump(mode="json"),
        )
    )


def _refund_amount(request: ReturnRequest) -> tuple[Decimal, str]:
    total = Decimal("0")
    for line in request.items:
        total += line.order_item.unit_price * line.quantity
    currency = request.order.currency
    return total, currency


def _build_timeline(
    request: ReturnRequest,
    shipment: ReturnShipment | None,
    refund: ReturnRefund | None,
) -> list[FulfillmentTimelineStep]:
    status = request.status
    steps: list[FulfillmentTimelineStep] = []
    for key, label, done_when in _WORKFLOW_STEPS:
        completed = status in done_when
        current = False
        if key == "approved" and status in {ReturnStatus.APPROVED, ReturnStatus.LABEL_PENDING}:
            current = True
        elif key == "label" and status == ReturnStatus.LABEL_GENERATED:
            current = True
        elif key == "transit" and status == ReturnStatus.RETURN_IN_TRANSIT:
            current = True
        elif key == "received" and status == ReturnStatus.RECEIVED:
            current = True
        elif key == "refund_pending" and status == ReturnStatus.REFUND_PENDING:
            current = True
        elif key == "refund_done" and status == ReturnStatus.REFUND_COMPLETED:
            current = True
        if key == "label" and shipment and shipment.status == ShipmentProviderStatus.FAILED:
            completed = False
            current = status == ReturnStatus.LABEL_PENDING
        if key == "refund_pending" and refund and refund.status == RefundProviderStatus.FAILED:
            current = True
        steps.append(FulfillmentTimelineStep(key=key, label=label, completed=completed, current=current))
    return steps


def _shipment_public(row: ReturnShipment) -> ShipmentPublic:
    return ShipmentPublic(
        id=row.id,
        status=row.status,
        carrier=row.carrier,
        tracking_number=row.tracking_number,
        label_url=row.label_url,
        provider_ref=row.provider_ref,
        failure_reason=row.failure_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _refund_public(row: ReturnRefund) -> RefundPublic:
    return RefundPublic(
        id=row.id,
        status=row.status,
        amount=row.amount,
        currency=row.currency,
        provider_ref=row.provider_ref,
        failure_reason=row.failure_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _notification_public(row: ReturnNotificationEvent) -> NotificationPublic:
    return NotificationPublic(
        id=row.id,
        event_type=row.event_type,
        recipient_email=row.recipient_email,
        subject=row.subject,
        body_preview=row.body_preview,
        mock_delivered=row.mock_delivered,
        created_at=row.created_at,
    )


def _action_result(
    request: ReturnRequest,
    shipment: ReturnShipment | None,
    refund: ReturnRefund | None,
    *,
    message: str | None = None,
) -> FulfillmentActionResult:
    return FulfillmentActionResult(
        return_status=request.status,
        shipment=_shipment_public(shipment) if shipment else None,
        refund=_refund_public(refund) if refund else None,
        message=message,
    )