"""Simulated logistics — no carrier API calls."""

from __future__ import annotations

import uuid

from app.providers.logistics.base import LabelRequestResult


class MockLogisticsProvider:
    def request_label(self, *, return_ref: str, idempotency_key: str) -> LabelRequestResult:
        if "fail-label" in idempotency_key.lower():
            return LabelRequestResult(
                provider_ref=f"mock-shp-fail-{return_ref[:8]}",
                status="FAILED",
                carrier="MOCK_CARRIER",
                tracking_number=None,
                label_url=None,
                failure_reason="Mock carrier could not generate a label",
            )
        tracking = f"MOCK1Z{uuid.uuid4().hex[:12].upper()}"
        return LabelRequestResult(
            provider_ref=f"mock-shp-{idempotency_key[:12]}",
            status="LABEL_READY",
            carrier="MOCK_CARRIER",
            tracking_number=tracking,
            label_url=f"https://mock.returnflow.local/labels/{tracking}.pdf",
            failure_reason=None,
        )

    def shipment_status(self, provider_ref: str) -> str:
        if "fail" in provider_ref:
            return "FAILED"
        return "IN_TRANSIT"