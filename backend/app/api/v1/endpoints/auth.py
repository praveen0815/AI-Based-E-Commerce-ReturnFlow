"""Registration, login, logout, and the current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_bearer_token, get_current_user, get_db, get_redis_client
from app.core.config import Settings, get_settings
from app.core.responses import success_body
from app.models.user import User
from app.schemas.auth import (
    AuthResult,
    CurrentUserData,
    LoginRequest,
    MembershipPublic,
    RegisterRequest,
    TokenData,
    UserPublic,
)
from app.services.auth import login_user, logout_user, membership_views, register_user
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )


@router.post("/register", status_code=201, summary="Create an account")
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    await enforce_rate_limit(
        redis,
        scope="register",
        client_key=_client_ip(request) or "unknown",
        limit=settings.auth_rate_limit_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    user, token, expires_in = await register_user(
        session,
        redis,
        settings,
        email=str(payload.email),
        password=payload.password.get_secret_value(),
        display_name=payload.display_name,
        ip_address=_client_ip(request),
    )
    body = AuthResult(token=TokenData(access_token=token, expires_in=expires_in), user=_user_public(user))
    return JSONResponse(status_code=201, content=success_body(body, _request_id(request)))


@router.post("/login", summary="Sign in")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    await enforce_rate_limit(
        redis,
        scope="login",
        client_key=_client_ip(request) or "unknown",
        limit=settings.auth_rate_limit_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    user, token, expires_in = await login_user(
        session,
        redis,
        settings,
        email=str(payload.email),
        password=payload.password.get_secret_value(),
        ip_address=_client_ip(request),
    )
    body = AuthResult(token=TokenData(access_token=token, expires_in=expires_in), user=_user_public(user))
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("/logout", summary="Invalidate the current access token")
async def logout(
    request: Request,
    token: str = Depends(get_bearer_token),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    await logout_user(
        session,
        redis,
        token=token,
        secret=settings.jwt_secret,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body({"status": "logged_out"}, _request_id(request)))


@router.get("/me", summary="Current user and store memberships")
async def me(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    memberships = [MembershipPublic.model_validate(item) for item in await membership_views(session, user.id)]
    body = CurrentUserData(user=_user_public(user), memberships=memberships)
    return JSONResponse(content=success_body(body, _request_id(request)))
