"""Persisted LangGraph AI return review runs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.ai_review_enums import AiReviewRunStatus
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReturnAiReviewRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_ai_review_runs"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    return_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    started_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[AiReviewRunStatus] = mapped_column(
        Enum(AiReviewRunStatus, name="ai_review_run_status", native_enum=True, create_type=False),
        nullable=False,
    )
    current_agent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    state_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["ReturnAiReviewEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ReturnAiReviewEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "return_ai_review_events"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("return_ai_review_runs.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped[ReturnAiReviewRun] = relationship(back_populates="events")