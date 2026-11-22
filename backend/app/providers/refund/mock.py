"""Simulated refund provider — no money movement."""

from __future__ import annotations

from decimal import Decimal

from app.providers.refund.base import RefundEligibilityResult, RefundInitiationResult


class MockRefundProvider:
    def check_eligibility(self, *, amount: Decimal, currency: str, order_ref: str) -> RefundEligibilityResult:
        if amount <= 0:
            return RefundEligibilityResult(eligible=False, reason="Amount must be positive")
        return RefundEligibilityResult(eligible=True, reason=None)

    def initiate_refund(
        self, *, amount: Decimal, currency: str, order_ref: str, idempotency_key: str
    ) -> RefundInitiationResult:
        if "fail-refund" in idempotency_key.lower():
            return RefundInitiationResult(
                provider_ref=f"mock-rfd-fail-{order_ref[:8]}",
                status="FAILED",
                failure_reason="Mock provider rejected the refund",
            )
        return RefundInitiationResult(
            provider_ref=f"mock-rfd-{idempotency_key[:12]}",
            status="PROCESSING",
            failure_reason=None,
        )

    def get_status(self, provider_ref: str) -> str:
        if "fail" in provider_ref:
            return "FAILED"
        return "COMPLETED"