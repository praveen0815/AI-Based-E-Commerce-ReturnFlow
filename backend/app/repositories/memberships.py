"""Store membership lookups.

Queries are scoped by the caller. A store id from the client is never used
unless it already matched one of that user's memberships.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.permissions import MemberRole
from app.models.membership import StoreMembership
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository):
    async def list_for_user(self, user_id: uuid.UUID) -> list[StoreMembership]:
        result = await self.session.execute(
            select(StoreMembership)
            .options(selectinload(StoreMembership.store))
            .where(StoreMembership.user_id == user_id)
            .order_by(StoreMembership.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_for_user(self, user_id: uuid.UUID, store_id: uuid.UUID) -> StoreMembership | None:
        result = await self.session.execute(
            select(StoreMembership)
            .options(selectinload(StoreMembership.store), selectinload(StoreMembership.user))
            .where(
                StoreMembership.user_id == user_id,
                StoreMembership.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_store(self, store_id: uuid.UUID) -> list[StoreMembership]:
        result = await self.session.execute(
            select(StoreMembership)
            .options(selectinload(StoreMembership.user))
            .where(StoreMembership.store_id == store_id)
            .order_by(StoreMembership.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_in_store(self, store_id: uuid.UUID, membership_id: uuid.UUID) -> StoreMembership | None:
        result = await self.session.execute(
            select(StoreMembership)
            .options(selectinload(StoreMembership.user))
            .where(
                StoreMembership.id == membership_id,
                StoreMembership.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_owners(self, store_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(StoreMembership)
            .where(
                StoreMembership.store_id == store_id,
                StoreMembership.role == MemberRole.OWNER,
            )
        )
        return int(result.scalar_one())

    def add(self, membership: StoreMembership) -> None:
        self.session.add(membership)
