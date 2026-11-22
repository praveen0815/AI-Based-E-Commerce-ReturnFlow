"""Order and payment status values."""

from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"