"""Store policy rule versions."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update

from app.models.store_policy_rules import StoreReturnPolicyRule
from app.repositories.base import BaseRepository


class PolicyRulesRepository(BaseRepository):
    def add(self, row: StoreReturnPolicyRule) -> None:
        self.session.add(row)

    async def get_active(self, store_id: uuid.UUID) -> StoreReturnPolicyRule | None:
        stmt = (
            select(StoreReturnPolicyRule)
            .where(StoreReturnPolicyRule.store_id == store_id, StoreReturnPolicyRule.is_active.is_(True))
            .order_by(StoreReturnPolicyRule.version.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def max_version(self, store_id: uuid.UUID) -> int:
        stmt = select(StoreReturnPolicyRule.version).where(StoreReturnPolicyRule.store_id == store_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return max(rows) if rows else 0

    async def deactivate_all(self, store_id: uuid.UUID) -> None:
        await self.session.execute(
            update(StoreReturnPolicyRule)
            .where(StoreReturnPolicyRule.store_id == store_id, StoreReturnPolicyRule.is_active.is_(True))
            .values(is_active=False)
        )