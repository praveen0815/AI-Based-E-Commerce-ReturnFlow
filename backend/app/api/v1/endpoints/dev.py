"""Development helpers. Disabled in production."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_permission
from app.core.config import Settings, get_settings
from app.core.permissions import Permission
from app.core.responses import success_body
from app.services.dev_seed import create_sample_commerce

router = APIRouter(prefix="/stores/current/dev")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.post("/sample-commerce", summary="Load labeled sample orders for development")
async def load_sample_commerce(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.STORE_READ)),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    body = await create_sample_commerce(
        session,
        settings,
        store_id=context.store.id,
        actor=context.user,
        role=context.membership.role,
        ip_address=request.client.host if request.client else None,
    )
    return JSONResponse(status_code=201, content=success_body(body, _request_id(request)))