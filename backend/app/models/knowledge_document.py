"""Store-scoped policy and knowledge documents."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.knowledge_enums import KnowledgeDocumentType, KnowledgeProcessingStatus
from app.core.rag_enums import KnowledgeIndexStatus
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StoreKnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "store_knowledge_documents"

    store_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    document_type: Mapped[KnowledgeDocumentType] = mapped_column(
        Enum(KnowledgeDocumentType, name="knowledge_document_type", native_enum=True, create_type=False),
        nullable=False,
    )
    processing_status: Mapped[KnowledgeProcessingStatus] = mapped_column(
        Enum(KnowledgeProcessingStatus, name="knowledge_processing_status", native_enum=True, create_type=False),
        nullable=False,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    index_status: Mapped[KnowledgeIndexStatus] = mapped_column(
        Enum(KnowledgeIndexStatus, name="knowledge_index_status", native_enum=True, create_type=False),
        nullable=False,
        default=KnowledgeIndexStatus.NOT_INDEXED,
        server_default="NOT_INDEXED",
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    store = relationship("Store", back_populates="knowledge_documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])