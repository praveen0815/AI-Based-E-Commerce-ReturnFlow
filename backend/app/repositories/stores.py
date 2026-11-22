"""Store lookups."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.store import Store
from app.repositories.base import BaseRepository


class StoreRepository(BaseRepository):
    async def get_by_id(self, store_id: uuid.UUID) -> Store | None:
        return await self.session.get(Store, store_id)

    async def get_by_slug(self, slug: str) -> Store | None:
        result = await self.session.execute(select(Store).where(Store.slug == slug))
        return result.scalar_one_or_none()

    def add(self, store: Store) -> None:
        self.session.add(store)
