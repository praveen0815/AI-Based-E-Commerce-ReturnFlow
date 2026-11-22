"""Store and customer analytics payloads."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class AdminKpis(BaseModel):
    total_orders: int
    total_return_requests: int
    pending_review: int
    approved_returns: int
    rejected_returns: int
    completed_refunds: int
    refund_value: Decimal
    return_rate_percent: Decimal | None = Field(description="Returns divided by orders, 0-100 when orders exist")


class TimeSeriesPoint(BaseModel):
    bucket: date
    value: Decimal


class CountSeriesPoint(BaseModel):
    label: str
    count: int


class ProductReturnFrequency(BaseModel):
    sku: str
    line_name: str
    return_quantity: int


class ProcessingDurationStats(BaseModel):
    sample_size: int
    avg_hours_to_decision: Decimal | None
    avg_hours_to_completion: Decimal | None


class AiHumanComparison(BaseModel):
    runs_with_recommendation: int
    aligned: int
    ai_approve_actual_approve: int
    ai_deny_actual_deny: int
    mismatches: int
    escalated_without_decision: int


class AdminAnalytics(BaseModel):
    kpis: AdminKpis
    returns_over_time: list[TimeSeriesPoint]
    return_reasons: list[CountSeriesPoint]
    return_status_distribution: list[CountSeriesPoint]
    refund_amounts_over_time: list[TimeSeriesPoint]
    product_return_frequency: list[ProductReturnFrequency]
    processing_duration: ProcessingDurationStats
    ai_human_comparison: AiHumanComparison


class CustomerRefundRow(BaseModel):
    return_number: str
    amount: Decimal
    currency: str
    status: str
    completed_at: str | None


class CustomerKpis(BaseModel):
    order_count: int
    active_returns: int
    completed_returns: int
    refund_total: Decimal
    currency: str | None


class CustomerAnalytics(BaseModel):
    kpis: CustomerKpis
    active_return_statuses: list[CountSeriesPoint]
    refunds: list[CustomerRefundRow]