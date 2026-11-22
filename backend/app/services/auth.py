"""Registration, login, logout, and the current user."""

from __future__ import annotations

import uuid
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.permissions import permissions_for
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    session_key,
    verify_password_or_dummy,
)
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.users import UserRepository
from app.services.audit import record_audit


async def register_user(
    session: AsyncSession,
    redis: Redis,
    settings: Settings,
    *,
    email: str,
    password: str,
    display_name: str,
    ip_address: str | None,
) -> tuple[User, str, int]:
    users = UserRepository(session)
    if await users.get_by_email(email) is not None:
        raise AppError(
            "An account with that email already exists",
            code="email_taken",
            status_code=409,
        )
    user = User(email=email, password_hash=hash_password(password), display_name=display_name.strip())
    users.add(user)
    await session.flush()
    token, _token_id, expires_in = await _issue_token(redis, settings, user.id)
    await record_audit(
        session,
        action="user.registered",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=ip_address,
    )
    await session.commit()
    await session.refresh(user)
    return user, token, expires_in


async def login_user(
    session: AsyncSession,
    redis: Redis,
    settings: Settings,
    *,
    email: str,
    password: str,
    ip_address: str | None,
) -> tuple[User, str, int]:
    user = await UserRepository(session).get_by_email(email)
    password_hash = user.password_hash if user is not None and user.is_active else None
    if not verify_password_or_dummy(password_hash, password) or user is None or not user.is_active:
        await record_audit(
            session,
            action="auth.login_failed",
            actor_user_id=user.id if user is not None else None,
            ip_address=ip_address,
            details={"email": email},
        )
        await session.commit()
        raise AppError("Invalid email or password", code="invalid_credentials", status_code=401)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    token, _token_id, expires_in = await _issue_token(redis, settings, user.id)
    await record_audit(
        session,
        action="auth.login_succeeded",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=ip_address,
    )
    await session.commit()
    return user, token, expires_in


async def logout_user(
    session: AsyncSession,
    redis: Redis,
    *,
    token: str,
    secret: str,
    ip_address: str | None,
) -> None:
    payload = decode_access_token(token, secret)
    token_id = str(payload["jti"])
    subject = str(payload["sub"])
    try:
        stored = await redis.get(session_key(token_id))
        if stored != subject:
            raise AppError("Authentication required", code="not_authenticated", status_code=401)
        await redis.delete(session_key(token_id))
    except RedisError as exc:
        raise AppError(
            "Authentication is temporarily unavailable",
            code="auth_backend_unavailable",
            status_code=503,
        ) from exc
    await record_audit(
        session,
        action="auth.logout",
        actor_user_id=uuid.UUID(str(payload["sub"])),
        target_type="session",
        target_id=token_id,
        ip_address=ip_address,
    )
    await session.commit()


async def authenticate_token(
    session: AsyncSession,
    redis: Redis,
    *,
    token: str,
    secret: str,
) -> User:
    payload = decode_access_token(token, secret)
    token_id = str(payload["jti"])
    subject = str(payload["sub"])
    try:
        stored = await redis.get(session_key(token_id))
    except RedisError as exc:
        raise AppError(
            "Authentication is temporarily unavailable",
            code="auth_backend_unavailable",
            status_code=503,
        ) from exc
    if stored != subject:
        raise AppError("Authentication required", code="not_authenticated", status_code=401)
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AppError("Authentication required", code="not_authenticated", status_code=401) from exc
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError("Authentication required", code="not_authenticated", status_code=401)
    return user


async def membership_views(session: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    memberships = await MembershipRepository(session).list_for_user(user_id)
    return [
        {
            "id": membership.id,
            "store_id": membership.store_id,
            "store_name": membership.store.name,
            "store_slug": membership.store.slug,
            "role": membership.role,
            "permissions": sorted(permission.value for permission in permissions_for(membership.role)),
        }
        for membership in memberships
    ]


async def _issue_token(redis: Redis, settings: Settings, user_id: uuid.UUID) -> tuple[str, str, int]:
    token, token_id, expires_in = create_access_token(
        user_id=user_id,
        secret=settings.jwt_secret,
        ttl_seconds=settings.access_token_ttl_seconds,
    )
    try:
        await redis.set(session_key(token_id), str(user_id), ex=expires_in)
    except RedisError as exc:
        raise AppError(
            "Authentication is temporarily unavailable",
            code="auth_backend_unavailable",
            status_code=503,
        ) from exc
    return token, token_id, expires_in
