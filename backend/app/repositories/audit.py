"""Audit log writes and store-scoped reads."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    def add(self, entry: AuditLog) -> None:
        self.session.add(entry)

    async def list_for_store(self, store_id: uuid.UUID, limit: int = 50) -> list[tuple[AuditLog, str | None]]:
        result = await self.session.execute(
            select(AuditLog, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(AuditLog.store_id == store_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [(entry, email) for entry, email in result.all()]
