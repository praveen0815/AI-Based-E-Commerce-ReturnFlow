"""Policy assistant thumbs-up/down feedback."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class PolicyChatFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "policy_chat_feedback"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer_excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)