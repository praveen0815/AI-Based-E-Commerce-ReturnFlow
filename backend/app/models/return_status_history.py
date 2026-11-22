"""Append-only return status changes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.return_lifecycle import ReturnStatus
from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.models.return_request import ReturnRequest
from app.models.user import User


class ReturnStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "return_status_history"

    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[ReturnStatus | None] = mapped_column(
        Enum(ReturnStatus, name="return_status", native_enum=True, create_type=False),
        nullable=True,
    )
    to_status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus, name="return_status", native_enum=True, create_type=False),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    return_request: Mapped[ReturnRequest] = relationship(back_populates="status_history")
    actor: Mapped[User | None] = relationship()