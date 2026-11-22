"""Customer orders within a store."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.order_enums import OrderStatus, PaymentStatus
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.store import Store
from app.models.user import User

if TYPE_CHECKING:
    from app.models.order_item import OrderItem


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("store_id", "order_number", name="uq_orders_store_number"),)

    store_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fulfillment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", native_enum=True, create_type=False),
        nullable=False,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=True, create_type=False),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    return_window_days: Mapped[int] = mapped_column(nullable=False, default=30, server_default="30")

    store: Mapped[Store] = relationship()
    customer: Mapped[User] = relationship()
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")