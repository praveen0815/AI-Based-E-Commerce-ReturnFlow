"""Membership of a user in one store."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.permissions import MemberRole
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.store import Store
from app.models.user import User


class StoreMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "store_memberships"
    __table_args__ = (
        UniqueConstraint("store_id", "user_id", name="uq_store_memberships_store_user"),
        Index("ix_store_memberships_user_id", "user_id"),
        Index("ix_store_memberships_store_id", "store_id"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="store_member_role", native_enum=True, create_type=False),
        nullable=False,
    )

    store: Mapped[Store] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
