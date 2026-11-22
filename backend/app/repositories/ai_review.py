"""AI review run persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.return_ai_review import ReturnAiReviewEvent, ReturnAiReviewRun
from app.repositories.base import BaseRepository


class AiReviewRepository(BaseRepository):
    def add(self, run: ReturnAiReviewRun) -> None:
        self.session.add(run)

    def add_event(self, event: ReturnAiReviewEvent) -> None:
        self.session.add(event)

    async def get_run_in_store(self, store_id: uuid.UUID, run_id: uuid.UUID) -> ReturnAiReviewRun | None:
        stmt = (
            select(ReturnAiReviewRun)
            .options(selectinload(ReturnAiReviewRun.events))
            .where(ReturnAiReviewRun.id == run_id, ReturnAiReviewRun.store_id == store_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_for_return(self, store_id: uuid.UUID, return_id: uuid.UUID) -> ReturnAiReviewRun | None:
        stmt = (
            select(ReturnAiReviewRun)
            .where(ReturnAiReviewRun.store_id == store_id, ReturnAiReviewRun.return_request_id == return_id)
            .order_by(ReturnAiReviewRun.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_events(self, run_id: uuid.UUID) -> list[ReturnAiReviewEvent]:
        stmt = select(ReturnAiReviewEvent).where(ReturnAiReviewEvent.run_id == run_id).order_by(ReturnAiReviewEvent.sequence)
        return list((await self.session.execute(stmt)).scalars().all())

    async def next_sequence(self, run_id: uuid.UUID) -> int:
        rows = await self.list_events(run_id)
        if not rows:
            return 1
        return max(event.sequence for event in rows) + 1