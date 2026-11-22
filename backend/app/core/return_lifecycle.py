"""Return request status and allowed transitions."""

from __future__ import annotations

from enum import Enum

from app.core.exceptions import AppError


class ReturnStatus(str, Enum):
    REQUESTED = "REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    LABEL_PENDING = "LABEL_PENDING"
    LABEL_GENERATED = "LABEL_GENERATED"
    RETURN_IN_TRANSIT = "RETURN_IN_TRANSIT"
    RECEIVED = "RECEIVED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUND_PROCESSING = "REFUND_PROCESSING"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXCHANGE_PROCESSING = "EXCHANGE_PROCESSING"


class RequestedResolution(str, Enum):
    REFUND = "REFUND"
    EXCHANGE = "EXCHANGE"
    STORE_CREDIT = "STORE_CREDIT"


TERMINAL_STATUSES = frozenset({ReturnStatus.REJECTED, ReturnStatus.CANCELLED, ReturnStatus.COMPLETED})

ALLOWED_TRANSITIONS: dict[ReturnStatus, frozenset[ReturnStatus]] = {
    ReturnStatus.REQUESTED: frozenset({ReturnStatus.UNDER_REVIEW, ReturnStatus.CANCELLED}),
    ReturnStatus.UNDER_REVIEW: frozenset(
        {ReturnStatus.APPROVED, ReturnStatus.REJECTED, ReturnStatus.CANCELLED}
    ),
    ReturnStatus.APPROVED: frozenset(
        {
            ReturnStatus.LABEL_PENDING,
            ReturnStatus.RETURN_IN_TRANSIT,
            ReturnStatus.EXCHANGE_PROCESSING,
            ReturnStatus.CANCELLED,
        }
    ),
    ReturnStatus.LABEL_PENDING: frozenset({ReturnStatus.LABEL_GENERATED, ReturnStatus.CANCELLED}),
    ReturnStatus.LABEL_GENERATED: frozenset({ReturnStatus.RETURN_IN_TRANSIT, ReturnStatus.CANCELLED}),
    ReturnStatus.RETURN_IN_TRANSIT: frozenset({ReturnStatus.RECEIVED, ReturnStatus.CANCELLED}),
    ReturnStatus.RECEIVED: frozenset(
        {
            ReturnStatus.REFUND_PENDING,
            ReturnStatus.REFUND_PROCESSING,
            ReturnStatus.EXCHANGE_PROCESSING,
            ReturnStatus.COMPLETED,
        }
    ),
    ReturnStatus.REFUND_PENDING: frozenset({ReturnStatus.REFUND_COMPLETED, ReturnStatus.RECEIVED}),
    ReturnStatus.REFUND_PROCESSING: frozenset({ReturnStatus.REFUND_COMPLETED, ReturnStatus.COMPLETED}),
    ReturnStatus.REFUND_COMPLETED: frozenset({ReturnStatus.COMPLETED}),
    ReturnStatus.EXCHANGE_PROCESSING: frozenset({ReturnStatus.COMPLETED}),
    ReturnStatus.REJECTED: frozenset(),
    ReturnStatus.CANCELLED: frozenset(),
    ReturnStatus.COMPLETED: frozenset(),
}

CUSTOMER_CANCEL_FROM = frozenset({ReturnStatus.REQUESTED, ReturnStatus.UNDER_REVIEW})


def assert_transition(current: ReturnStatus, new_status: ReturnStatus) -> None:
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise AppError(
            f"Cannot move a return from {current.value} to {new_status.value}",
            code="invalid_return_transition",
            status_code=409,
        )


def can_customer_cancel(status: ReturnStatus) -> bool:
    return status in CUSTOMER_CANCEL_FROM