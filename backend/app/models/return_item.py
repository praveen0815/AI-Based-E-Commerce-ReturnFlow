"""Items included in a return request."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.order_item import OrderItem
from app.models.return_request import ReturnRequest


class ReturnItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_items"

    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    return_request: Mapped[ReturnRequest] = relationship(back_populates="items")
    order_item: Mapped[OrderItem] = relationship()