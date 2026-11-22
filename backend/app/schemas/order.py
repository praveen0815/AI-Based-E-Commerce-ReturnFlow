"""Order and line-item payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.core.order_enums import OrderStatus, PaymentStatus


class OrderItemPublic(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    line_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    item_metadata: dict[str, Any]
    returnable_quantity: int | None = None


class OrderPublic(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_user_id: uuid.UUID
    customer_email: str | None = None
    customer_display_name: str | None = None
    order_date: datetime
    fulfillment_date: datetime | None
    status: OrderStatus
    payment_status: PaymentStatus
    currency: str
    total_amount: Decimal
    is_sample: bool
    return_window_days: int
    return_window_ends_at: datetime | None = None
    items: list[OrderItemPublic] = Field(default_factory=list)


class OrderListFilters(BaseModel):
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: str = Field(default="order_date")
    direction: str = Field(default="desc")
    status: OrderStatus | None = None
    payment_status: PaymentStatus | None = None
    q: str | None = Field(default=None, max_length=120)