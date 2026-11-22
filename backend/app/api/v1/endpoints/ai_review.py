"""LangGraph AI return review."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.schemas.ai_review import AiReviewResumeRequest
from app.services.ai_review.service import (
    get_review_output,
    get_review_run,
    latest_review,
    list_review_events,
    resume_review,
    start_ai_review,
)

router = APIRouter(prefix="/stores/current/returns")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/{return_id}/ai-review", summary="Start AI return review", status_code=201)
async def start_review(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await start_ai_review(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor_id=context.user.id,
        role=context.membership.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(status_code=201, content=success_body(body, _request_id(request)))


@router.get("/{return_id}/ai-review/latest", summary="Latest AI review for return")
async def latest_ai_review(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await latest_review(session, store_id=context.store.id, return_id=return_id, role=context.membership.role)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/{return_id}/ai-review/runs/{run_id}", summary="AI review run status")
async def review_status(
    request: Request,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await get_review_run(
        session,
        store_id=context.store.id,
        return_id=return_id,
        run_id=run_id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/{return_id}/ai-review/runs/{run_id}/events", summary="Agent event history")
async def review_events(
    request: Request,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    events = await list_review_events(
        session,
        store_id=context.store.id,
        return_id=return_id,
        run_id=run_id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body({"events": events}, _request_id(request)))


@router.get("/{return_id}/ai-review/runs/{run_id}/output", summary="Structured review output")
async def review_output(
    request: Request,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await get_review_output(
        session,
        store_id=context.store.id,
        return_id=return_id,
        run_id=run_id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/{return_id}/ai-review/runs/{run_id}/resume", summary="Human checkpoint resume")
async def resume_checkpoint(
    request: Request,
    return_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: AiReviewResumeRequest,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await resume_review(
        session,
        store_id=context.store.id,
        return_id=return_id,
        run_id=run_id,
        actor_id=context.user.id,
        role=context.membership.role,
        body=payload,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))