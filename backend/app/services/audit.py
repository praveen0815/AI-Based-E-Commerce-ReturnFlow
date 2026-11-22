"""Record security events without secrets."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit import AuditRepository

_SECRET_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "authorization",
    "jwt",
    "secret",
    "jwt_secret",
}


def scrub_details(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                continue
            scrubbed[str(key)] = scrub_details(item)
        return scrubbed
    if isinstance(value, list):
        return [scrub_details(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    store_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        store_id=store_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        details=scrub_details(details or {}),
    )
    AuditRepository(session).add(entry)
