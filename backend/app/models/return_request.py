"""Return requests tied to an order."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.return_lifecycle import RequestedResolution, ReturnStatus
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.order import Order
from app.models.store import Store
from app.models.user import User

if TYPE_CHECKING:
    from app.models.return_item import ReturnItem
    from app.models.return_status_history import ReturnStatusHistory


class ReturnRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_requests"
    __table_args__ = (UniqueConstraint("store_id", "return_number", name="uq_returns_store_number"),)

    store_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    return_number: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requested_resolution: Mapped[RequestedResolution] = mapped_column(
        Enum(RequestedResolution, name="return_requested_resolution", native_enum=True, create_type=False),
        nullable=False,
    )
    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus, name="return_status", native_enum=True, create_type=False),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    return_window_days: Mapped[int] = mapped_column(nullable=False)
    return_window_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    store: Mapped[Store] = relationship()
    order: Mapped[Order] = relationship()
    customer: Mapped[User] = relationship()
    items: Mapped[list[ReturnItem]] = relationship(back_populates="return_request", cascade="all, delete-orphan")
    status_history: Mapped[list[ReturnStatusHistory]] = relationship(
        back_populates="return_request",
        cascade="all, delete-orphan",
    )