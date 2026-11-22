"""Audit log payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditPublic(BaseModel):
    id: str
    action: str
    actor_email: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    details: dict[str, Any]
    created_at: datetime
