"""Fulfillment persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.return_fulfillment import (
    FulfillmentIdempotency,
    ReturnNotificationEvent,
    ReturnRefund,
    ReturnShipment,
)
from app.repositories.base import BaseRepository


class FulfillmentRepository(BaseRepository):
    async def get_idempotency(self, store_id: uuid.UUID, idempotency_key: str) -> FulfillmentIdempotency | None:
        stmt = select(FulfillmentIdempotency).where(
            FulfillmentIdempotency.store_id == store_id,
            FulfillmentIdempotency.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def save_idempotency(self, row: FulfillmentIdempotency) -> None:
        self.session.add(row)

    async def latest_shipment(self, return_request_id: uuid.UUID) -> ReturnShipment | None:
        stmt = (
            select(ReturnShipment)
            .where(ReturnShipment.return_request_id == return_request_id)
            .order_by(ReturnShipment.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def shipment_by_idempotency(self, store_id: uuid.UUID, idempotency_key: str) -> ReturnShipment | None:
        stmt = select(ReturnShipment).where(
            ReturnShipment.store_id == store_id,
            ReturnShipment.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add_shipment(self, row: ReturnShipment) -> None:
        self.session.add(row)

    async def latest_refund(self, return_request_id: uuid.UUID) -> ReturnRefund | None:
        stmt = (
            select(ReturnRefund)
            .where(ReturnRefund.return_request_id == return_request_id)
            .order_by(ReturnRefund.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def refund_by_idempotency(self, store_id: uuid.UUID, idempotency_key: str) -> ReturnRefund | None:
        stmt = select(ReturnRefund).where(
            ReturnRefund.store_id == store_id,
            ReturnRefund.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add_refund(self, row: ReturnRefund) -> None:
        self.session.add(row)

    async def list_notifications(self, return_request_id: uuid.UUID) -> list[ReturnNotificationEvent]:
        stmt = (
            select(ReturnNotificationEvent)
            .where(ReturnNotificationEvent.return_request_id == return_request_id)
            .order_by(ReturnNotificationEvent.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add_notification(self, row: ReturnNotificationEvent) -> None:
        self.session.add(row)