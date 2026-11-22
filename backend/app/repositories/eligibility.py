"""Eligibility decision persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.return_eligibility_decision import ReturnEligibilityDecision
from app.repositories.base import BaseRepository


class EligibilityDecisionRepository(BaseRepository):
    def add(self, row: ReturnEligibilityDecision) -> None:
        self.session.add(row)

    async def get_in_store(self, store_id: uuid.UUID, decision_id: uuid.UUID) -> ReturnEligibilityDecision | None:
        stmt = select(ReturnEligibilityDecision).where(
            ReturnEligibilityDecision.id == decision_id,
            ReturnEligibilityDecision.store_id == store_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_for_return(
        self,
        store_id: uuid.UUID,
        return_request_id: uuid.UUID,
    ) -> ReturnEligibilityDecision | None:
        stmt = (
            select(ReturnEligibilityDecision)
            .where(
                ReturnEligibilityDecision.store_id == store_id,
                ReturnEligibilityDecision.return_request_id == return_request_id,
            )
            .order_by(ReturnEligibilityDecision.evaluated_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()