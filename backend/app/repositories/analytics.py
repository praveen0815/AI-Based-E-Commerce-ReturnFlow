"""Store-scoped analytics queries."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select

from app.core.fulfillment_enums import RefundProviderStatus
from app.core.return_lifecycle import ReturnStatus
from app.models.order import Order
from app.models.return_ai_review import ReturnAiReviewRun
from app.models.return_fulfillment import ReturnRefund
from app.models.return_item import ReturnItem
from app.models.return_request import ReturnRequest
from app.models.order_item import OrderItem
from app.repositories.base import BaseRepository

_PENDING_REVIEW = frozenset({ReturnStatus.REQUESTED, ReturnStatus.UNDER_REVIEW})
_APPROVED_STATUSES = frozenset(
    {
        ReturnStatus.APPROVED,
        ReturnStatus.LABEL_PENDING,
        ReturnStatus.LABEL_GENERATED,
        ReturnStatus.RETURN_IN_TRANSIT,
        ReturnStatus.RECEIVED,
        ReturnStatus.REFUND_PENDING,
        ReturnStatus.REFUND_PROCESSING,
        ReturnStatus.REFUND_COMPLETED,
        ReturnStatus.EXCHANGE_PROCESSING,
        ReturnStatus.COMPLETED,
    }
)
_ACTIVE_CUSTOMER = frozenset(
    {
        ReturnStatus.REQUESTED,
        ReturnStatus.UNDER_REVIEW,
        ReturnStatus.APPROVED,
        ReturnStatus.LABEL_PENDING,
        ReturnStatus.LABEL_GENERATED,
        ReturnStatus.RETURN_IN_TRANSIT,
        ReturnStatus.RECEIVED,
        ReturnStatus.REFUND_PENDING,
        ReturnStatus.REFUND_PROCESSING,
        ReturnStatus.EXCHANGE_PROCESSING,
    }
)


class AnalyticsRepository(BaseRepository):
    async def count_orders(self, store_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.store_id == store_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_orders_for_customer(self, store_id: uuid.UUID, customer_user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.store_id == store_id, Order.customer_user_id == customer_user_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def return_counts_by_status(self, store_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(ReturnRequest.status, func.count())
            .where(ReturnRequest.store_id == store_id)
            .group_by(ReturnRequest.status)
        )
        result = await self.session.execute(stmt)
        return {row[0].value: int(row[1]) for row in result.all()}

    async def return_counts_by_status_customer(
        self, store_id: uuid.UUID, customer_user_id: uuid.UUID
    ) -> dict[str, int]:
        stmt = (
            select(ReturnRequest.status, func.count())
            .where(ReturnRequest.store_id == store_id, ReturnRequest.customer_user_id == customer_user_id)
            .group_by(ReturnRequest.status)
        )
        result = await self.session.execute(stmt)
        return {row[0].value: int(row[1]) for row in result.all()}

    async def count_completed_refunds(self, store_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ReturnRefund)
            .where(ReturnRefund.store_id == store_id, ReturnRefund.status == RefundProviderStatus.COMPLETED)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def sum_refund_value(self, store_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(ReturnRefund.amount), 0)).where(
            ReturnRefund.store_id == store_id,
            ReturnRefund.status == RefundProviderStatus.COMPLETED,
        )
        result = await self.session.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def sum_refund_value_customer(self, store_id: uuid.UUID, customer_user_id: uuid.UUID) -> tuple[Decimal, str | None]:
        stmt = (
            select(func.coalesce(func.sum(ReturnRefund.amount), 0), func.min(ReturnRefund.currency))
            .select_from(ReturnRefund)
            .join(ReturnRequest, ReturnRequest.id == ReturnRefund.return_request_id)
            .where(
                ReturnRefund.store_id == store_id,
                ReturnRequest.customer_user_id == customer_user_id,
                ReturnRefund.status == RefundProviderStatus.COMPLETED,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return Decimal(str(row[0])), row[1]

    async def returns_over_time(self, store_id: uuid.UUID, *, since: datetime) -> list[tuple[datetime, int]]:
        bucket = func.date_trunc("day", ReturnRequest.submitted_at)
        stmt = (
            select(bucket, func.count())
            .where(ReturnRequest.store_id == store_id, ReturnRequest.submitted_at >= since)
            .group_by(bucket)
            .order_by(bucket.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in result.all()]

    async def return_reasons(self, store_id: uuid.UUID) -> list[tuple[str, int]]:
        stmt = (
            select(ReturnRequest.reason, func.count())
            .where(ReturnRequest.store_id == store_id)
            .group_by(ReturnRequest.reason)
            .order_by(func.count().desc())
            .limit(12)
        )
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in result.all()]

    async def refund_amounts_over_time(self, store_id: uuid.UUID, *, since: datetime) -> list[tuple[datetime, Decimal]]:
        bucket = func.date_trunc("day", ReturnRefund.updated_at)
        stmt = (
            select(bucket, func.coalesce(func.sum(ReturnRefund.amount), 0))
            .where(
                ReturnRefund.store_id == store_id,
                ReturnRefund.status == RefundProviderStatus.COMPLETED,
                ReturnRefund.updated_at >= since,
            )
            .group_by(bucket)
            .order_by(bucket.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], Decimal(str(row[1]))) for row in result.all()]

    async def product_return_frequency(self, store_id: uuid.UUID, *, limit: int = 10) -> list[tuple[str, str, int]]:
        stmt = (
            select(OrderItem.sku, OrderItem.line_name, func.coalesce(func.sum(ReturnItem.quantity), 0))
            .join(ReturnItem, ReturnItem.order_item_id == OrderItem.id)
            .join(ReturnRequest, ReturnRequest.id == ReturnItem.return_request_id)
            .where(ReturnRequest.store_id == store_id)
            .group_by(OrderItem.sku, OrderItem.line_name)
            .order_by(func.sum(ReturnItem.quantity).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1], int(row[2])) for row in result.all()]

    async def processing_duration_stats(self, store_id: uuid.UUID) -> tuple[int, Decimal | None, Decimal | None]:
        decision_hours = func.extract(
            "epoch", ReturnRequest.decision_at - ReturnRequest.submitted_at
        ) / 3600.0
        completion_hours = func.extract(
            "epoch", ReturnRequest.updated_at - ReturnRequest.submitted_at
        ) / 3600.0
        stmt = select(
            func.count(ReturnRequest.id),
            func.avg(case((ReturnRequest.decision_at.is_not(None), decision_hours), else_=None)),
            func.avg(case((ReturnRequest.status == ReturnStatus.COMPLETED, completion_hours), else_=None)),
        ).where(ReturnRequest.store_id == store_id)
        result = await self.session.execute(stmt)
        row = result.one()
        count = int(row[0] or 0)
        avg_decision = Decimal(str(row[1])).quantize(Decimal("0.01")) if row[1] is not None else None
        avg_completion = Decimal(str(row[2])).quantize(Decimal("0.01")) if row[2] is not None else None
        return count, avg_decision, avg_completion

    async def list_customer_refunds(
        self, store_id: uuid.UUID, customer_user_id: uuid.UUID, *, limit: int = 20
    ) -> list[tuple[str, Decimal, str, str, datetime | None]]:
        stmt = (
            select(
                ReturnRequest.return_number,
                ReturnRefund.amount,
                ReturnRefund.currency,
                ReturnRefund.status,
                ReturnRefund.updated_at,
            )
            .join(ReturnRequest, ReturnRequest.id == ReturnRefund.return_request_id)
            .where(ReturnRefund.store_id == store_id, ReturnRequest.customer_user_id == customer_user_id)
            .order_by(ReturnRefund.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def ai_review_comparison_rows(self, store_id: uuid.UUID) -> list[tuple[str | None, str]]:
        stmt = (
            select(ReturnAiReviewRun.output_payload, ReturnRequest.status)
            .join(ReturnRequest, ReturnRequest.id == ReturnAiReviewRun.return_request_id)
            .where(
                ReturnAiReviewRun.store_id == store_id,
                ReturnAiReviewRun.output_payload.is_not(None),
            )
        )
        result = await self.session.execute(stmt)
        rows: list[tuple[str | None, str]] = []
        for payload, status in result.all():
            recommendation = None
            if payload and isinstance(payload, dict):
                final = payload.get("finalization") or {}
                if isinstance(final, dict):
                    recommendation = final.get("recommendation")
            rows.append((recommendation, status.value))
        return rows


def pending_review_count(by_status: dict[str, int]) -> int:
    return sum(by_status.get(s.value, 0) for s in _PENDING_REVIEW)


def approved_count(by_status: dict[str, int]) -> int:
    return sum(by_status.get(s.value, 0) for s in _APPROVED_STATUSES)


def active_returns_count(by_status: dict[str, int]) -> int:
    return sum(by_status.get(s.value, 0) for s in _ACTIVE_CUSTOMER)


def completed_returns_count(by_status: dict[str, int]) -> int:
    return by_status.get(ReturnStatus.COMPLETED.value, 0) + by_status.get(ReturnStatus.REJECTED.value, 0)


def compute_return_rate(total_returns: int, total_orders: int) -> Decimal | None:
    if total_orders <= 0:
        return None
    return (Decimal(total_returns) / Decimal(total_orders) * Decimal("100")).quantize(Decimal("0.01"))


def since_days(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _map_actual_outcome(status_value: str) -> str | None:
    if status_value == ReturnStatus.REJECTED.value:
        return "DENY"
    if status_value in {s.value for s in _APPROVED_STATUSES}:
        return "APPROVE_FOR_PROCESSING"
    return None