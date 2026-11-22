"""Account profile for the authenticated user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.responses import success_body
from app.models.user import User
from app.schemas.auth import ProfileUpdate, UserPublic
from app.services.audit import record_audit

router = APIRouter(prefix="/profile")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _user_public(user: User) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name, is_active=user.is_active)


@router.get("", summary="Account profile")
async def read_profile(request: Request, user: User = Depends(get_current_user)) -> JSONResponse:
    return JSONResponse(content=success_body(_user_public(user), _request_id(request)))


@router.patch("", summary="Update the display name")
async def update_profile(
    payload: ProfileUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user.display_name = payload.display_name
    await record_audit(
        session,
        action="profile.updated",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        details={"display_name": user.display_name},
    )
    await session.commit()
    await session.refresh(user)
    return JSONResponse(content=success_body(_user_public(user), _request_id(request)))
