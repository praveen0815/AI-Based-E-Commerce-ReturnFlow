"""Fulfillment API models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.fulfillment_enums import RefundProviderStatus, ShipmentProviderStatus
from app.core.return_lifecycle import ReturnStatus


class ShipmentPublic(BaseModel):
    id: uuid.UUID
    status: ShipmentProviderStatus
    carrier: str
    tracking_number: str | None
    label_url: str | None
    provider_ref: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class RefundPublic(BaseModel):
    id: uuid.UUID
    status: RefundProviderStatus
    amount: Decimal
    currency: str
    provider_ref: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class NotificationPublic(BaseModel):
    id: uuid.UUID
    event_type: str
    recipient_email: str
    subject: str
    body_preview: str
    mock_delivered: bool
    created_at: datetime


class FulfillmentTimelineStep(BaseModel):
    key: str
    label: str
    completed: bool
    current: bool


class FulfillmentSnapshot(BaseModel):
    return_id: uuid.UUID
    return_status: ReturnStatus
    shipment: ShipmentPublic | None
    refund: RefundPublic | None
    notifications: list[NotificationPublic]
    timeline: list[FulfillmentTimelineStep]


class FulfillmentActionResult(BaseModel):
    return_status: ReturnStatus
    shipment: ShipmentPublic | None = None
    refund: RefundPublic | None = None
    message: str | None = None


class RefundRetryRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)