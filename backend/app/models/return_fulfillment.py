"""Return shipment, refund, and notification records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.fulfillment_enums import RefundProviderStatus, ShipmentProviderStatus
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReturnShipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_shipments"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"))
    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ShipmentProviderStatus] = mapped_column(
        Enum(ShipmentProviderStatus, name="shipment_provider_status", native_enum=True, create_type=False),
        nullable=False,
    )
    carrier: Mapped[str] = mapped_column(String(64), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ReturnRefund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_refunds"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"))
    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[RefundProviderStatus] = mapped_column(
        Enum(RefundProviderStatus, name="refund_provider_status", native_enum=True, create_type=False),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ReturnNotificationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "return_notification_events"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"))
    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_preview: Mapped[str] = mapped_column(String(500), nullable=False)
    mock_delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FulfillmentIdempotency(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "fulfillment_idempotency"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)