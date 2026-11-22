"""Tenant stores."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.knowledge_document import StoreKnowledgeDocument
    from app.models.membership import StoreMembership


class Store(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    memberships: Mapped[list[StoreMembership]] = relationship(back_populates="store")
    knowledge_documents: Mapped[list["StoreKnowledgeDocument"]] = relationship(back_populates="store")
