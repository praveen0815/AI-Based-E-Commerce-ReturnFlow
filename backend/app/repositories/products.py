"""Product lookups."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    def add(self, product: Product) -> None:
        self.session.add(product)

    async def get_in_store(self, store_id: uuid.UUID, product_id: uuid.UUID) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.store_id == store_id)
        )
        return result.scalar_one_or_none()