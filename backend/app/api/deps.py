"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.permissions import Permission, has_permission
from app.database.redis import get_redis
from app.database.session import get_session_factory
from app.models.membership import StoreMembership
from app.models.store import Store
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.services.auth import authenticate_token

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a transaction-scoped session and roll back on failure."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_redis_client() -> Redis:
    """Return the process-wide Redis client."""

    return get_redis()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AppError("Authentication required", code="not_authenticated", status_code=401)
    return await authenticate_token(
        session,
        redis,
        token=credentials.credentials,
        secret=settings.jwt_secret,
    )


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AppError("Authentication required", code="not_authenticated", status_code=401)
    return credentials.credentials


@dataclass(frozen=True)
class StoreContext:
    """A membership proven to belong to the authenticated user."""

    user: User
    membership: StoreMembership
    store: Store


async def get_store_context(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    store_id: uuid.UUID | None = Header(default=None, alias="X-Store-ID"),
) -> StoreContext:
    memberships = await MembershipRepository(session).list_for_user(user.id)
    if store_id is None:
        if len(memberships) == 1:
            membership = memberships[0]
        elif not memberships:
            raise AppError("Create or join a store first", code="store_required", status_code=403)
        else:
            raise AppError("Choose a store", code="store_selection_required", status_code=409)
    else:
        membership = next((item for item in memberships if item.store_id == store_id), None)
        if membership is None:
            raise AppError("Store access denied", code="store_forbidden", status_code=403)
    return StoreContext(user=user, membership=membership, store=membership.store)


def require_permission(permission: Permission):
    """Build a dependency that checks the caller's verified membership role."""

    async def checker(context: StoreContext = Depends(get_store_context)) -> StoreContext:
        if not has_permission(context.membership.role, permission):
            raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
        return context

    return checker


def require_any_store_permission(*permissions: Permission):
    """Allow the request when the membership has any of the listed permissions."""

    async def checker(context: StoreContext = Depends(get_store_context)) -> StoreContext:
        if not any(has_permission(context.membership.role, permission) for permission in permissions):
            raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
        return context

    return checker
