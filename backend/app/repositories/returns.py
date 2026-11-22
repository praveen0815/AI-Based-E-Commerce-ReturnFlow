"""Return request queries."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.return_lifecycle import ReturnStatus
from app.models.order import Order
from app.models.return_item import ReturnItem as ReturnLine
from app.models.return_request import ReturnRequest
from app.models.user import User
from app.repositories.base import BaseRepository

_RETURN_SORT = {
    "submitted_at": ReturnRequest.submitted_at,
    "return_number": ReturnRequest.return_number,
    "status": ReturnRequest.status,
}

_QUEUE_STATUSES = (
    ReturnStatus.REQUESTED,
    ReturnStatus.UNDER_REVIEW,
    ReturnStatus.APPROVED,
    ReturnStatus.LABEL_PENDING,
    ReturnStatus.LABEL_GENERATED,
    ReturnStatus.RETURN_IN_TRANSIT,
    ReturnStatus.RECEIVED,
    ReturnStatus.REFUND_PENDING,
    ReturnStatus.REFUND_PROCESSING,
)


class ReturnRepository(BaseRepository):
    def add(self, request: ReturnRequest) -> None:
        self.session.add(request)

    async def get_in_store(
        self,
        store_id: uuid.UUID,
        return_id: uuid.UUID,
        *,
        customer_user_id: uuid.UUID | None = None,
    ) -> ReturnRequest | None:
        stmt = (
            select(ReturnRequest)
            .options(
                selectinload(ReturnRequest.items).selectinload(ReturnLine.order_item),
                selectinload(ReturnRequest.order),
                selectinload(ReturnRequest.customer),
            )
            .where(ReturnRequest.id == return_id, ReturnRequest.store_id == store_id)
        )
        if customer_user_id is not None:
            stmt = stmt.where(ReturnRequest.customer_user_id == customer_user_id)
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
        status: ReturnStatus | None,
        q: str | None,
        queue: bool,
    ) -> tuple[list[ReturnRequest], int]:
        base: Select[tuple[ReturnRequest]] = select(ReturnRequest).where(ReturnRequest.store_id == store_id)
        if customer_user_id is not None:
            base = base.where(ReturnRequest.customer_user_id == customer_user_id)
        if queue:
            base = base.where(ReturnRequest.status.in_(_QUEUE_STATUSES))
            if status is not None:
                base = base.where(ReturnRequest.status == status)
        elif status is not None:
            base = base.where(ReturnRequest.status == status)
        if q:
            term = f"%{q.strip().lower()}%"
            base = (
                base.join(Order, Order.id == ReturnRequest.order_id)
                .outerjoin(User, User.id == ReturnRequest.customer_user_id)
                .where(
                    or_(
                        func.lower(ReturnRequest.return_number).like(term),
                        func.lower(Order.order_number).like(term),
                        func.lower(User.email).like(term),
                    )
                )
            )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        sort_col = _RETURN_SORT.get(sort, ReturnRequest.submitted_at)
        ordered = base.order_by(sort_col.asc() if direction == "asc" else sort_col.desc())
        offset = (page - 1) * page_size
        page_stmt = (
            ordered.options(
                selectinload(ReturnRequest.items).selectinload(ReturnLine.order_item),
                selectinload(ReturnRequest.order),
                selectinload(ReturnRequest.customer),
            )
            .offset(offset)
            .limit(page_size)
        )
        items = list((await self.session.execute(page_stmt)).scalars().all())
        return items, total

    async def list_status_history(self, return_id: uuid.UUID) -> list[tuple]:
        from app.models.return_status_history import ReturnStatusHistory

        result = await self.session.execute(
            select(ReturnStatusHistory, User.email)
            .outerjoin(User, User.id == ReturnStatusHistory.actor_user_id)
            .where(ReturnStatusHistory.return_request_id == return_id)
            .order_by(ReturnStatusHistory.created_at.asc())
        )
        return list(result.all())

    async def returned_quantity(self, order_item_id: uuid.UUID) -> int:
        from app.models.return_item import ReturnItem

        terminal = (ReturnStatus.CANCELLED, ReturnStatus.REJECTED)
        result = await self.session.execute(
            select(func.coalesce(func.sum(ReturnItem.quantity), 0))
            .select_from(ReturnItem)
            .join(ReturnRequest, ReturnRequest.id == ReturnItem.return_request_id)
            .where(
                ReturnItem.order_item_id == order_item_id,
                ReturnRequest.status.notin_(terminal),
            )
        )
        return int(result.scalar_one())