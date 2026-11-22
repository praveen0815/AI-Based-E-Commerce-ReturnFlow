"""Permission-aware analytics."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.permissions import MemberRole, Permission, has_permission
from app.core.return_lifecycle import ReturnStatus
from app.repositories.analytics import (
    AnalyticsRepository,
    _map_actual_outcome,
    active_returns_count,
    approved_count,
    completed_returns_count,
    compute_return_rate,
    pending_review_count,
    since_days,
)
from app.schemas.analytics import (
    AdminAnalytics,
    AdminKpis,
    AiHumanComparison,
    CountSeriesPoint,
    CustomerAnalytics,
    CustomerKpis,
    CustomerRefundRow,
    ProcessingDurationStats,
    ProductReturnFrequency,
    TimeSeriesPoint,
)


def _ai_human_rows(rows: list[tuple[str | None, str]]) -> AiHumanComparison:
    comparison = AiHumanComparison(
        runs_with_recommendation=0,
        aligned=0,
        ai_approve_actual_approve=0,
        ai_deny_actual_deny=0,
        mismatches=0,
        escalated_without_decision=0,
    )
    for recommendation, status_value in rows:
        if not recommendation:
            comparison.escalated_without_decision += 1
            continue
        comparison.runs_with_recommendation += 1
        actual = _map_actual_outcome(status_value)
        if actual is None:
            comparison.escalated_without_decision += 1
            continue
        if recommendation == actual:
            comparison.aligned += 1
            if recommendation == "APPROVE_FOR_PROCESSING":
                comparison.ai_approve_actual_approve += 1
            elif recommendation == "DENY":
                comparison.ai_deny_actual_deny += 1
        elif recommendation == "ESCALATE_HUMAN":
            comparison.escalated_without_decision += 1
        else:
            comparison.mismatches += 1
    return comparison


async def admin_analytics(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    role: MemberRole,
    days: int,
) -> AdminAnalytics:
    if not has_permission(role, Permission.RETURN_READ):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    repo = AnalyticsRepository(session)
    since = since_days(days)
    by_status = await repo.return_counts_by_status(store_id)
    total_returns = sum(by_status.values())
    total_orders = await repo.count_orders(store_id)
    refund_value = await repo.sum_refund_value(store_id)

    kpis = AdminKpis(
        total_orders=total_orders,
        total_return_requests=total_returns,
        pending_review=pending_review_count(by_status),
        approved_returns=approved_count(by_status),
        rejected_returns=by_status.get(ReturnStatus.REJECTED.value, 0),
        completed_refunds=await repo.count_completed_refunds(store_id),
        refund_value=refund_value,
        return_rate_percent=compute_return_rate(total_returns, total_orders),
    )

    returns_over_time = [
        TimeSeriesPoint(bucket=_as_date(bucket), value=Decimal(bucket_count))
        for bucket, bucket_count in await repo.returns_over_time(store_id, since=since)
    ]
    return_reasons = [CountSeriesPoint(label=label, count=count) for label, count in await repo.return_reasons(store_id)]
    return_status_distribution = [
        CountSeriesPoint(label=label, count=count) for label, count in sorted(by_status.items(), key=lambda x: -x[1])
    ]
    refund_amounts = [
        TimeSeriesPoint(bucket=_as_date(bucket), value=amount)
        for bucket, amount in await repo.refund_amounts_over_time(store_id, since=since)
    ]
    products = [
        ProductReturnFrequency(sku=sku, line_name=name, return_quantity=qty)
        for sku, name, qty in await repo.product_return_frequency(store_id)
    ]
    sample_size, avg_decision, avg_completion = await repo.processing_duration_stats(store_id)
    processing = ProcessingDurationStats(
        sample_size=sample_size,
        avg_hours_to_decision=avg_decision,
        avg_hours_to_completion=avg_completion,
    )
    ai_rows = await repo.ai_review_comparison_rows(store_id)

    return AdminAnalytics(
        kpis=kpis,
        returns_over_time=returns_over_time,
        return_reasons=return_reasons,
        return_status_distribution=return_status_distribution,
        refund_amounts_over_time=refund_amounts,
        product_return_frequency=products,
        processing_duration=processing,
        ai_human_comparison=_ai_human_rows(ai_rows),
    )


async def customer_analytics(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    customer_user_id: uuid.UUID,
    role: MemberRole,
) -> CustomerAnalytics:
    if not has_permission(role, Permission.RETURN_READ_OWN):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    if has_permission(role, Permission.RETURN_READ):
        raise AppError("Use the admin analytics endpoint for staff roles", code="forbidden", status_code=403)

    repo = AnalyticsRepository(session)
    by_status = await repo.return_counts_by_status_customer(store_id, customer_user_id)
    refund_total, currency = await repo.sum_refund_value_customer(store_id, customer_user_id)

    active_statuses = [
        CountSeriesPoint(label=label, count=count)
        for label, count in sorted(by_status.items(), key=lambda x: -x[1])
        if count > 0
    ]

    refunds = [
        CustomerRefundRow(
            return_number=number,
            amount=amount,
            currency=cur,
            status=status.value if hasattr(status, "value") else str(status),
            completed_at=updated.isoformat() if updated else None,
        )
        for number, amount, cur, status, updated in await repo.list_customer_refunds(store_id, customer_user_id)
    ]

    return CustomerAnalytics(
        kpis=CustomerKpis(
            order_count=await repo.count_orders_for_customer(store_id, customer_user_id),
            active_returns=active_returns_count(by_status),
            completed_returns=completed_returns_count(by_status),
            refund_total=refund_total,
            currency=currency,
        ),
        active_return_statuses=active_statuses,
        refunds=refunds,
    )


def _as_date(value) -> date:
    if hasattr(value, "date"):
        return value.date()
    return date.fromisoformat(str(value)[:10])