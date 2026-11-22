"""Line items on an order."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.order import Order
from app.models.product import Product


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    line_name: Mapped[str] = mapped_column(String(160), nullable=False)
    item_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship()