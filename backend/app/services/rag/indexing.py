"""Index processed knowledge documents into Chroma."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.knowledge_enums import KnowledgeProcessingStatus
from app.core.rag_enums import KnowledgeIndexStatus
from app.models.knowledge_document import StoreKnowledgeDocument
from app.repositories.knowledge import KnowledgeDocumentRepository
from app.services.knowledge_files import sanitize_processing_error
from app.services.rag.chunking import chunk_document_text
from app.services.rag.chroma_store import delete_document_chunks, upsert_chunks
from app.services.rag.embeddings import get_embeddings_provider

logger = logging.getLogger(__name__)


async def index_document(session: AsyncSession, *, store_id: uuid.UUID, document_id: uuid.UUID) -> StoreKnowledgeDocument:
    repo = KnowledgeDocumentRepository(session)
    document = await repo.get_in_store(store_id, document_id)
    if document is None:
        raise AppError("Document not found", code="not_found", status_code=404)
    if document.processing_status != KnowledgeProcessingStatus.PROCESSED or not document.extracted_text:
        raise AppError("Document text is not ready for indexing", code="not_ready", status_code=409)

    document.index_status = KnowledgeIndexStatus.INDEXING
    document.index_error = None
    await session.commit()

    settings = get_settings()
    try:
        chunks = await asyncio.to_thread(
            chunk_document_text,
            document.extracted_text,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            page_count=document.page_count,
        )
        if not chunks:
            raise ValueError("No chunks were produced from extracted text")
        embeddings = await asyncio.to_thread(
            get_embeddings_provider(settings).embed_documents,
            [chunk.text for chunk in chunks],
        )
        ids = [f"{document.id}:{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "store_id": str(store_id),
                "document_id": str(document.id),
                "document_type": document.document_type.value,
                "original_filename": document.original_filename,
                "chunk_index": chunk.chunk_index,
                "section_label": chunk.section_label,
                "page_hint": chunk.page_hint or "",
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
            }
            for chunk in chunks
        ]
        await asyncio.to_thread(delete_document_chunks, store_id, document.id)
        await asyncio.to_thread(
            upsert_chunks,
            store_id,
            ids=ids,
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadatas,
        )
        document.index_status = KnowledgeIndexStatus.INDEXED
        document.indexed_chunk_count = len(chunks)
        document.indexed_at = datetime.now(UTC)
        document.index_error = None
    except Exception as exc:  # noqa: BLE001
        logger.exception("knowledge_index_failed document_id=%s", document_id)
        document.index_status = KnowledgeIndexStatus.INDEX_FAILED
        document.indexed_chunk_count = None
        document.index_error = sanitize_processing_error(str(exc))
    await session.commit()
    await session.refresh(document)
    return document


async def reindex_store(session: AsyncSession, *, store_id: uuid.UUID) -> dict:
    stmt = select(StoreKnowledgeDocument).where(
        StoreKnowledgeDocument.store_id == store_id,
        StoreKnowledgeDocument.processing_status == KnowledgeProcessingStatus.PROCESSED,
    )
    documents = list((await session.execute(stmt)).scalars().all())
    indexed = 0
    failed = 0
    for document in documents:
        updated = await index_document(session, store_id=store_id, document_id=document.id)
        if updated.index_status == KnowledgeIndexStatus.INDEXED:
            indexed += 1
        else:
            failed += 1
    return {"indexed": indexed, "failed": failed, "total": len(documents)}


async def delete_index(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    document_id: uuid.UUID | None,
) -> dict:
    if document_id is None:
        from app.services.rag.chroma_store import delete_store_index

        await asyncio.to_thread(delete_store_index, store_id)
        stmt = select(StoreKnowledgeDocument).where(StoreKnowledgeDocument.store_id == store_id)
        for document in (await session.execute(stmt)).scalars().all():
            document.index_status = KnowledgeIndexStatus.NOT_INDEXED
            document.indexed_at = None
            document.indexed_chunk_count = None
            document.index_error = None
        await session.commit()
        return {"deleted": "store", "documents_reset": True}

    repo = KnowledgeDocumentRepository(session)
    document = await repo.get_in_store(store_id, document_id)
    if document is None:
        raise AppError("Document not found", code="not_found", status_code=404)
    await asyncio.to_thread(delete_document_chunks, store_id, document_id)
    document.index_status = KnowledgeIndexStatus.NOT_INDEXED
    document.indexed_at = None
    document.indexed_chunk_count = None
    document.index_error = None
    await session.commit()
    return {"deleted": str(document_id)}