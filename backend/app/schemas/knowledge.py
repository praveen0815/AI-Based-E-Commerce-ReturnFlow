"""Knowledge document API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.knowledge_enums import KnowledgeDocumentType, KnowledgeProcessingStatus
from app.core.rag_enums import KnowledgeIndexStatus

_PREVIEW_CHARS = 400


class KnowledgeDocumentPublic(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    uploaded_at: datetime
    document_type: KnowledgeDocumentType
    processing_status: KnowledgeProcessingStatus
    page_count: int | None
    text_preview: str | None = None
    extracted_text: str | None = None
    error_message: str | None = None
    uploaded_by_user_id: uuid.UUID | None
    index_status: KnowledgeIndexStatus
    indexed_at: datetime | None
    indexed_chunk_count: int | None
    index_error: str | None

    @classmethod
    def from_model(
        cls,
        document,
        *,
        include_full_text: bool = False,
    ) -> "KnowledgeDocumentPublic":
        preview = None
        if document.extracted_text:
            preview = document.extracted_text[:_PREVIEW_CHARS]
            if len(document.extracted_text) > _PREVIEW_CHARS:
                preview = f"{preview}..."
        return cls(
            id=document.id,
            store_id=document.store_id,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            file_size_bytes=document.file_size_bytes,
            uploaded_at=document.uploaded_at,
            document_type=document.document_type,
            processing_status=document.processing_status,
            page_count=document.page_count,
            text_preview=preview,
            extracted_text=document.extracted_text if include_full_text else None,
            error_message=document.error_message,
            uploaded_by_user_id=document.uploaded_by_user_id,
            index_status=document.index_status,
            indexed_at=document.indexed_at,
            indexed_chunk_count=document.indexed_chunk_count,
            index_error=document.index_error,
        )


class KnowledgeDocumentListPublic(BaseModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    uploaded_at: datetime
    document_type: KnowledgeDocumentType
    processing_status: KnowledgeProcessingStatus
    page_count: int | None
    text_preview: str | None
    error_message: str | None
    index_status: KnowledgeIndexStatus
    indexed_at: datetime | None
    indexed_chunk_count: int | None

    @classmethod
    def from_model(cls, document) -> "KnowledgeDocumentListPublic":
        full = KnowledgeDocumentPublic.from_model(document, include_full_text=False)
        return cls(
            id=full.id,
            original_filename=full.original_filename,
            mime_type=full.mime_type,
            file_size_bytes=full.file_size_bytes,
            uploaded_at=full.uploaded_at,
            document_type=full.document_type,
            processing_status=full.processing_status,
            page_count=full.page_count,
            text_preview=full.text_preview,
            error_message=full.error_message,
            index_status=full.index_status,
            indexed_at=full.indexed_at,
            indexed_chunk_count=full.indexed_chunk_count,
        )


class KnowledgeUploadForm(BaseModel):
    document_type: KnowledgeDocumentType = Field(default=KnowledgeDocumentType.RETURN_POLICY)