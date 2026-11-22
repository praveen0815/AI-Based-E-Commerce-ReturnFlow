"""Refund provider interface."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class RefundEligibilityResult:
    eligible: bool
    reason: str | None


@dataclass(frozen=True)
class RefundInitiationResult:
    provider_ref: str
    status: str
    failure_reason: str | None = None


class RefundProvider(Protocol):
    def check_eligibility(self, *, amount: Decimal, currency: str, order_ref: str) -> RefundEligibilityResult: ...

    def initiate_refund(
        self, *, amount: Decimal, currency: str, order_ref: str, idempotency_key: str
    ) -> RefundInitiationResult: ...

    def get_status(self, provider_ref: str) -> str: ...