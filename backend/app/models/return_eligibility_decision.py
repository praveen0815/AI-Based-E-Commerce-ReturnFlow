"""Audit record for a deterministic eligibility evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.eligibility_enums import EligibilityDecision
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReturnEligibilityDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_eligibility_decisions"

    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    return_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("return_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    decision: Mapped[EligibilityDecision] = mapped_column(
        Enum(EligibilityDecision, name="eligibility_decision", native_enum=True, create_type=False),
        nullable=False,
    )
    decision_code: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    decision_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_rule_version: Mapped[int] = mapped_column(nullable=False)
    policy_references: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    missing_information: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    recommended_next_steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_review_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)