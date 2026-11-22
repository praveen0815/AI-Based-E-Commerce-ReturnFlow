"""Execute graph with timeout and persist events."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.ai_review_enums import AiReviewRunStatus
from app.core.config import get_settings
from app.database.session import get_session_factory
from app.models.return_ai_review import ReturnAiReviewEvent, ReturnAiReviewRun
from app.repositories.ai_review import AiReviewRepository
from app.services.ai_review.graph import build_review_graph
from app.services.ai_review.tools import load_return_context, tool_evaluate_eligibility, tool_search_policies

logger = logging.getLogger(__name__)

_GRAPH = build_review_graph()
_active: set[asyncio.Task[None]] = set()


def schedule_ai_review(run_id: uuid.UUID) -> None:
    task = asyncio.create_task(_execute_run(run_id))
    _active.add(task)
    task.add_done_callback(_active.discard)


async def _execute_run(run_id: uuid.UUID) -> None:
    settings = get_settings()
    timeout = settings.ai_review_timeout_seconds
    session_factory = get_session_factory()
    async with session_factory() as session:
        run = (await session.execute(select(ReturnAiReviewRun).where(ReturnAiReviewRun.id == run_id))).scalar_one_or_none()
        if run is None:
            return
        repo = AiReviewRepository(session)
        run.status = AiReviewRunStatus.RUNNING
        run.current_agent = "INTAKE"
        await session.commit()

        try:
            context = await load_return_context(session, store_id=run.store_id, return_id=run.return_request_id)
            query = f"{context.reason} {context.description[:240]}"
            policy_hits = await tool_search_policies(run.store_id, query)
            eligibility = await tool_evaluate_eligibility(session, store_id=run.store_id, context=context)
            initial: dict[str, Any] = {
                "store_id": str(run.store_id),
                "return_id": str(run.return_request_id),
                "return_snapshot": {
                    "return_number": context.return_number,
                    "order_number": context.order_number,
                    "reason": context.reason,
                    "description": context.description,
                    "requested_resolution": context.requested_resolution.value,
                    "status": context.status,
                    "items": context.items,
                },
                "policy_hits": policy_hits,
                "eligibility": eligibility,
                "revision_count": run.revision_count,
                "event_log": [],
            }

            final = await asyncio.wait_for(asyncio.to_thread(_GRAPH.invoke, initial), timeout=timeout)
            run.output_payload = {
                "intake": final.get("intake"),
                "policy_research": final.get("policy_research"),
                "eligibility": final.get("eligibility_out"),
                "resolution": final.get("resolution"),
                "review": final.get("review"),
                "finalization": final.get("finalization"),
            }
            run.state_snapshot = {k: v for k, v in final.items() if k != "event_log"}
            run.revision_count = int(final.get("revision_count", run.revision_count))
            run.status = AiReviewRunStatus.AWAITING_HUMAN
            run.current_agent = None
            run.error_message = None

            seq = await repo.next_sequence(run.id)
            for entry in final.get("event_log", []):
                repo.add_event(
                    ReturnAiReviewEvent(
                        run_id=run.id,
                        sequence=seq,
                        agent=entry["agent"],
                        event_type=entry["event_type"],
                        payload=entry["payload"],
                    )
                )
                seq += 1
        except TimeoutError:
            logger.warning("ai_review_timed_out run_id=%s", run_id)
            run.status = AiReviewRunStatus.TIMED_OUT
            run.error_message = "Workflow exceeded the execution time limit"
            run.completed_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai_review_failed run_id=%s", run_id)
            run.status = AiReviewRunStatus.FAILED
            run.error_message = str(exc).replace("\n", " ")[:500]
            run.completed_at = datetime.now(UTC)
        await session.commit()