"""Return requests for the current store."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_any_store_permission, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.core.return_lifecycle import ReturnStatus
from app.schemas.pagination import Paginated
from app.schemas.return_request import ReturnCreate, ReturnPublic, ReturnStatusEventPublic, ReturnStatusUpdate
from app.services.returns import (
    cancel_return,
    create_return,
    get_return,
    get_return_history,
    list_returns,
    update_return_status,
)

router = APIRouter(prefix="/stores/current/returns")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.get("", summary="List return requests")
async def list_return_requests(
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("submitted_at"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    status: ReturnStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
) -> JSONResponse:
    items, total = await list_returns(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        page=page,
        page_size=page_size,
        sort=sort,
        direction=direction,
        status=status,
        q=q,
        queue=False,
    )
    body = Paginated[ReturnPublic](items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/queue", summary="Open returns awaiting staff action")
async def return_queue(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("submitted_at"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    status: ReturnStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
) -> JSONResponse:
    items, total = await list_returns(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        page=page,
        page_size=page_size,
        sort=sort if sort in {"submitted_at", "return_number", "status"} else "submitted_at",
        direction="asc" if direction == "asc" else "desc",
        status=status,
        q=q,
        queue=True,
    )
    body = Paginated[ReturnPublic](items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("", status_code=201, summary="Create a return request")
async def create_return_request(
    payload: ReturnCreate,
    request: Request,
    context: StoreContext = Depends(require_any_store_permission(Permission.RETURN_CREATE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await create_return(
        session,
        store_id=context.store.id,
        actor=context.user,
        role=context.membership.role,
        payload=payload,
        ip_address=_client_ip(request),
    )
    return JSONResponse(status_code=201, content=success_body(body, _request_id(request)))


@router.get("/{return_id}", summary="Return detail")
async def return_detail(
    return_id: uuid.UUID,
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await get_return(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor_id=context.user.id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/{return_id}/history", summary="Return status timeline")
async def return_history(
    return_id: uuid.UUID,
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    events = await get_return_history(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor_id=context.user.id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body({"events": events}, _request_id(request)))


@router.post("/{return_id}/cancel", summary="Cancel a return request")
async def cancel_return_request(
    return_id: uuid.UUID,
    request: Request,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_CREATE, Permission.RETURN_MANAGE)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await cancel_return(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.patch("/{return_id}/status", summary="Review or advance a return")
async def change_return_status(
    return_id: uuid.UUID,
    payload: ReturnStatusUpdate,
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await update_return_status(
        session,
        store_id=context.store.id,
        return_id=return_id,
        actor=context.user,
        role=context.membership.role,
        payload=payload,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(body, _request_id(request)))