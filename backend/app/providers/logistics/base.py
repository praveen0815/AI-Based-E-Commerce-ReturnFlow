from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LabelRequestResult:
    provider_ref: str
    status: str
    carrier: str
    tracking_number: str | None
    label_url: str | None
    failure_reason: str | None = None


class LogisticsProvider(Protocol):
    def request_label(self, *, return_ref: str, idempotency_key: str) -> LabelRequestResult: ...

    def shipment_status(self, provider_ref: str) -> str: ...