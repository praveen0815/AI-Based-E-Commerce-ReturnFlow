"""Store-scoped order queries."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.order_enums import OrderStatus, PaymentStatus
from app.models.order import Order
from app.models.user import User
from app.repositories.base import BaseRepository

_ORDER_SORT = {
    "order_date": Order.order_date,
    "order_number": Order.order_number,
    "total_amount": Order.total_amount,
    "status": Order.status,
}


class OrderRepository(BaseRepository):
    def add(self, order: Order) -> None:
        self.session.add(order)

    async def get_in_store(
        self,
        store_id: uuid.UUID,
        order_id: uuid.UUID,
        *,
        customer_user_id: uuid.UUID | None = None,
    ) -> Order | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.customer))
            .where(Order.id == order_id, Order.store_id == store_id)
        )
        if customer_user_id is not None:
            stmt = stmt.where(Order.customer_user_id == customer_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_store(
        self,
        store_id: uuid.UUID,
        *,
        customer_user_id: uuid.UUID | None,
        page: int,
        page_size: int,
        sort: str,
        direction: str,
        status: OrderStatus | None,
        payment_status: PaymentStatus | None,
        q: str | None,
    ) -> tuple[list[tuple[Order, str, str]], int]:
        base = select(Order).where(Order.store_id == store_id)
        if customer_user_id is not None:
            base = base.where(Order.customer_user_id == customer_user_id)
        if status is not None:
            base = base.where(Order.status == status)
        if payment_status is not None:
            base = base.where(Order.payment_status == payment_status)
        if q:
            term = f"%{q.strip().lower()}%"
            base = base.outerjoin(User, User.id == Order.customer_user_id).where(
                or_(
                    func.lower(Order.order_number).like(term),
                    func.lower(User.email).like(term),
                    func.lower(User.display_name).like(term),
                )
            )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        sort_col = _ORDER_SORT.get(sort, Order.order_date)
        ordered = base.order_by(sort_col.asc() if direction == "asc" else sort_col.desc())
        offset = (page - 1) * page_size
        page_stmt = (
            ordered.options(selectinload(Order.items), selectinload(Order.customer))
            .offset(offset)
            .limit(page_size)
        )
        orders = list((await self.session.execute(page_stmt)).scalars().all())
        rows: list[tuple[Order, str, str]] = []
        for order in orders:
            rows.append((order, order.customer.email, order.customer.display_name))
        return rows, total