"""Store analytics and dashboards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.services.analytics import admin_analytics, customer_analytics

router = APIRouter(prefix="/stores/current/analytics")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("/admin", summary="Admin KPIs and charts")
async def analytics_admin(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.RETURN_READ)),
    session: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
) -> JSONResponse:
    body = await admin_analytics(session, store_id=context.store.id, role=context.membership.role, days=days)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.get("/me", summary="Customer dashboard metrics")
async def analytics_customer(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.RETURN_READ_OWN)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await customer_analytics(
        session,
        store_id=context.store.id,
        customer_user_id=context.user.id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))