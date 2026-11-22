"""AI review API orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_review_enums import AiReviewRunStatus
from app.core.exceptions import AppError
from app.core.permissions import MemberRole, Permission, has_permission
from app.models.return_ai_review import ReturnAiReviewRun
from app.repositories.ai_review import AiReviewRepository
from app.repositories.returns import ReturnRepository
from app.schemas.ai_review import AiReviewEventPublic, AiReviewRunPublic, AiReviewResumeRequest
from app.services.ai_review.runner import schedule_ai_review
from app.services.audit import record_audit


async def start_ai_review(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    ip_address: str | None,
) -> AiReviewRunPublic:
    if not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    found = await ReturnRepository(session).get_in_store(store_id, return_id)
    if found is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)

    repo = AiReviewRepository(session)
    latest = await repo.latest_for_return(store_id, return_id)
    if latest and latest.status in {AiReviewRunStatus.PENDING, AiReviewRunStatus.RUNNING}:
        raise AppError("An AI review is already in progress", code="review_in_progress", status_code=409)

    run = ReturnAiReviewRun(
        store_id=store_id,
        return_request_id=return_id,
        started_by_user_id=actor_id,
        status=AiReviewRunStatus.PENDING,
        revision_count=0,
        started_at=datetime.now(UTC),
    )
    repo.add(run)
    await session.commit()
    await session.refresh(run)

    run.status = AiReviewRunStatus.RUNNING
    await session.commit()
    schedule_ai_review(run.id)

    await record_audit(
        session,
        store_id=store_id,
        actor_user_id=actor_id,
        action="return.ai_review_started",
        target_type="ai_review_run",
        target_id=str(run.id),
        ip_address=ip_address,
        details={"return_id": str(return_id)},
    )
    return AiReviewRunPublic.from_model(run)


async def get_review_run(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    role: MemberRole,
) -> AiReviewRunPublic:
    _assert_read(role)
    run = await AiReviewRepository(session).get_run_in_store(store_id, run_id)
    if run is None or run.return_request_id != return_id:
        raise AppError("Review run not found", code="not_found", status_code=404)
    return AiReviewRunPublic.from_model(run)


async def list_review_events(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    role: MemberRole,
) -> list[AiReviewEventPublic]:
    _assert_read(role)
    repo = AiReviewRepository(session)
    run = await repo.get_run_in_store(store_id, run_id)
    if run is None or run.return_request_id != return_id:
        raise AppError("Review run not found", code="not_found", status_code=404)
    rows = await repo.list_events(run_id)
    return [AiReviewEventPublic.from_model(row) for row in rows]


async def get_review_output(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    role: MemberRole,
) -> dict:
    _assert_read(role)
    run = await AiReviewRepository(session).get_run_in_store(store_id, run_id)
    if run is None or run.return_request_id != return_id:
        raise AppError("Review run not found", code="not_found", status_code=404)
    if not run.output_payload:
        return {"status": run.status.value, "output": None}
    return {"status": run.status.value, "output": run.output_payload}


async def resume_review(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    body: AiReviewResumeRequest,
    ip_address: str | None,
) -> AiReviewRunPublic:
    if not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    repo = AiReviewRepository(session)
    run = await repo.get_run_in_store(store_id, run_id)
    if run is None or run.return_request_id != return_id:
        raise AppError("Review run not found", code="not_found", status_code=404)
    if run.status != AiReviewRunStatus.AWAITING_HUMAN:
        raise AppError("This run is not awaiting human review", code="invalid_state", status_code=409)

    run.human_decision = body.decision
    run.human_note = body.note
    run.status = AiReviewRunStatus.COMPLETED
    run.completed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(run)

    await record_audit(
        session,
        store_id=store_id,
        actor_user_id=actor_id,
        action="return.ai_review_resumed",
        target_type="ai_review_run",
        target_id=str(run.id),
        ip_address=ip_address,
        details={"decision": body.decision},
    )
    return AiReviewRunPublic.from_model(run)


async def latest_review(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    role: MemberRole,
) -> AiReviewRunPublic | None:
    _assert_read(role)
    found = await ReturnRepository(session).get_in_store(store_id, return_id)
    if found is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    run = await AiReviewRepository(session).latest_for_return(store_id, return_id)
    if run is None:
        return None
    return AiReviewRunPublic.from_model(run)


def _assert_read(role: MemberRole) -> None:
    if not (
        has_permission(role, Permission.RETURN_READ)
        or has_permission(role, Permission.RETURN_READ_OWN)
        or has_permission(role, Permission.RETURN_MANAGE)
    ):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)