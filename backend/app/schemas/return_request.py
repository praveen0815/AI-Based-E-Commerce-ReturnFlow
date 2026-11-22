"""Return request payloads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.return_lifecycle import RequestedResolution, ReturnStatus


class ReturnLineCreate(BaseModel):
    order_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)


class ReturnCreate(BaseModel):
    order_id: uuid.UUID
    reason: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=2000)
    requested_resolution: RequestedResolution
    items: list[ReturnLineCreate] = Field(min_length=1, max_length=50)

    @field_validator("reason", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        return cleaned


class ReturnStatusUpdate(BaseModel):
    status: ReturnStatus
    note: str | None = Field(default=None, max_length=500)
    internal_notes: str | None = Field(default=None, max_length=4000)


class ReturnItemPublic(BaseModel):
    id: uuid.UUID
    order_item_id: uuid.UUID
    line_name: str
    sku: str
    quantity: int


class ReturnStatusEventPublic(BaseModel):
    id: uuid.UUID
    from_status: ReturnStatus | None
    to_status: ReturnStatus
    actor_email: str | None
    note: str | None
    created_at: datetime


class ReturnPublic(BaseModel):
    id: uuid.UUID
    return_number: str
    order_id: uuid.UUID
    order_number: str
    customer_user_id: uuid.UUID
    customer_email: str | None = None
    reason: str
    description: str
    requested_resolution: RequestedResolution
    status: ReturnStatus
    submitted_at: datetime
    decision_at: datetime | None
    return_window_days: int
    return_window_ends_at: datetime
    internal_notes: str | None = None
    items: list[ReturnItemPublic] = Field(default_factory=list)


class ReturnListFilters(BaseModel):
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: str = Field(default="submitted_at")
    direction: str = Field(default="desc")
    status: ReturnStatus | None = None
    q: str | None = Field(default=None, max_length=120)
    queue: bool = False