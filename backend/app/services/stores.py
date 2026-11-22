"""Store creation and membership changes.

Every mutation receives a membership that was already loaded for the
authenticated user. Store ids from the client are not consulted here.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.permissions import MemberRole
from app.models.membership import StoreMembership
from app.models.store import Store
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.stores import StoreRepository
from app.repositories.users import UserRepository
from app.services.audit import record_audit

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    slug = _SLUG_PATTERN.sub("-", name.lower()).strip("-")
    return slug[:48] or "store"


async def create_store(
    session: AsyncSession,
    *,
    owner: User,
    name: str,
    ip_address: str | None,
) -> tuple[Store, StoreMembership]:
    stores = StoreRepository(session)
    slug = await _unique_slug(stores, slugify(name))
    store = Store(name=name.strip(), slug=slug)
    stores.add(store)
    await session.flush()
    membership = StoreMembership(store_id=store.id, user_id=owner.id, role=MemberRole.OWNER)
    MembershipRepository(session).add(membership)
    await session.flush()
    await record_audit(
        session,
        action="store.created",
        actor_user_id=owner.id,
        store_id=store.id,
        target_type="store",
        target_id=str(store.id),
        ip_address=ip_address,
        details={"name": store.name},
    )
    await session.commit()
    await session.refresh(store)
    await session.refresh(membership)
    return store, membership


async def update_store(
    session: AsyncSession,
    *,
    actor: User,
    store: Store,
    name: str,
    ip_address: str | None,
) -> Store:
    store.name = name.strip()
    await record_audit(
        session,
        action="store.updated",
        actor_user_id=actor.id,
        store_id=store.id,
        target_type="store",
        target_id=str(store.id),
        ip_address=ip_address,
        details={"name": store.name},
    )
    await session.commit()
    await session.refresh(store)
    return store


async def add_member(
    session: AsyncSession,
    *,
    actor: User,
    actor_role: MemberRole,
    store_id: uuid.UUID,
    email: str,
    role: MemberRole,
    ip_address: str | None,
) -> StoreMembership:
    _assert_can_assign(actor_role, current=None, new_role=role)
    users = UserRepository(session)
    member = await users.get_by_email(email)
    if member is None or not member.is_active:
        raise AppError("No active account uses that email", code="user_not_found", status_code=404)
    memberships = MembershipRepository(session)
    existing = await memberships.get_for_user(member.id, store_id)
    if existing is not None:
        raise AppError("That account is already a member", code="membership_exists", status_code=409)
    membership = StoreMembership(store_id=store_id, user_id=member.id, role=role)
    memberships.add(membership)
    await session.flush()
    await record_audit(
        session,
        action="membership.created",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="membership",
        target_id=str(membership.id),
        ip_address=ip_address,
        details={"email": member.email, "role": role.value},
    )
    await session.commit()
    await session.refresh(membership)
    membership.user = member
    return membership


async def change_member_role(
    session: AsyncSession,
    *,
    actor: User,
    actor_role: MemberRole,
    store_id: uuid.UUID,
    membership_id: uuid.UUID,
    role: MemberRole,
    ip_address: str | None,
) -> StoreMembership:
    memberships = MembershipRepository(session)
    membership = await memberships.get_in_store(store_id, membership_id)
    if membership is None:
        raise AppError("Membership not found", code="membership_not_found", status_code=404)
    _assert_can_assign(actor_role, current=membership.role, new_role=role)
    if membership.role == MemberRole.OWNER and role != MemberRole.OWNER:
        await _assert_owner_remains(memberships, store_id)
    membership.role = role
    member = membership.user
    await record_audit(
        session,
        action="membership.updated",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="membership",
        target_id=str(membership.id),
        ip_address=ip_address,
        details={"email": member.email, "role": role.value},
    )
    await session.commit()
    await session.refresh(membership)
    membership.user = member
    return membership


async def remove_member(
    session: AsyncSession,
    *,
    actor: User,
    actor_role: MemberRole,
    store_id: uuid.UUID,
    membership_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    memberships = MembershipRepository(session)
    membership = await memberships.get_in_store(store_id, membership_id)
    if membership is None:
        raise AppError("Membership not found", code="membership_not_found", status_code=404)
    _assert_can_assign(actor_role, current=membership.role, new_role=None)
    if membership.role == MemberRole.OWNER:
        await _assert_owner_remains(memberships, store_id)
    email = membership.user.email
    await session.delete(membership)
    await record_audit(
        session,
        action="membership.removed",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="membership",
        target_id=str(membership_id),
        ip_address=ip_address,
        details={"email": email},
    )
    await session.commit()


def _assert_can_assign(actor_role: MemberRole, *, current: MemberRole | None, new_role: MemberRole | None) -> None:
    if actor_role not in {MemberRole.OWNER, MemberRole.ADMIN}:
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    if actor_role == MemberRole.OWNER:
        return
    if current == MemberRole.OWNER or new_role == MemberRole.OWNER:
        raise AppError("Only an owner can change an owner", code="forbidden", status_code=403)


async def _assert_owner_remains(memberships: MembershipRepository, store_id: uuid.UUID) -> None:
    if await memberships.count_owners(store_id) <= 1:
        raise AppError("The store must keep an owner", code="last_owner", status_code=409)


async def _unique_slug(stores: StoreRepository, base: str) -> str:
    if await stores.get_by_slug(base) is None:
        return base
    for _ in range(5):
        candidate = f"{base[:42]}-{uuid.uuid4().hex[:6]}"
        if await stores.get_by_slug(candidate) is None:
            return candidate
    raise AppError("Could not create a unique store address", code="slug_conflict", status_code=409)
