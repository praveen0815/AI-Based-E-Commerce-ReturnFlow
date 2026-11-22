"""Knowledge document upload, storage, and processing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.knowledge_enums import KnowledgeProcessingStatus
from app.core.rag_enums import KnowledgeIndexStatus
from app.database.session import get_session_factory
from app.models.knowledge_document import StoreKnowledgeDocument
from app.repositories.knowledge import KnowledgeDocumentRepository
from app.schemas.knowledge import KnowledgeDocumentListPublic, KnowledgeDocumentPublic
from app.services.knowledge_files import (
    ExtractionResult,
    extension_for_filename,
    expected_mime_for_extension,
    extract_text as _extract_text,
    resolve_storage_path,
    safe_original_filename,
    sanitize_processing_error,
    storage_relative_key,
    validate_file_content,
)

logger = logging.getLogger(__name__)

_processing_tasks: set[asyncio.Task[None]] = set()


def _storage_root() -> Path:
    settings = get_settings()
    root = Path(settings.knowledge_storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def upload_knowledge_document(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor_id: uuid.UUID,
    filename: str,
    content: bytes,
    document_type,
) -> KnowledgeDocumentPublic:
    settings = get_settings()
    if len(content) > settings.knowledge_max_upload_bytes:
        raise AppError(
            f"File exceeds the {settings.knowledge_max_upload_bytes // (1024 * 1024)} MB limit",
            code="file_too_large",
            status_code=413,
        )

    original = safe_original_filename(filename)
    ext = extension_for_filename(original)
    validate_file_content(content, ext)

    document_id = uuid.uuid4()
    storage_key = storage_relative_key(store_id, document_id, ext)
    root = _storage_root()
    destination = resolve_storage_path(root, storage_key)
    destination.parent.mkdir(parents=True, exist_ok=False)
    destination.write_bytes(content)

    document = StoreKnowledgeDocument(
        id=document_id,
        store_id=store_id,
        uploaded_by_user_id=actor_id,
        original_filename=original,
        storage_key=storage_key,
        mime_type=expected_mime_for_extension(ext),
        file_size_bytes=len(content),
        uploaded_at=datetime.now(UTC),
        document_type=document_type,
        processing_status=KnowledgeProcessingStatus.UPLOADED,
        page_count=None,
        extracted_text=None,
        error_message=None,
        index_status=KnowledgeIndexStatus.NOT_INDEXED,
    )
    repo = KnowledgeDocumentRepository(session)
    repo.add(document)
    await session.commit()
    await session.refresh(document)
    schedule_document_processing(document_id)
    return KnowledgeDocumentPublic.from_model(document)


async def list_knowledge_documents(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    page: int,
    page_size: int,
    sort: str,
    direction: str,
    document_type,
    processing_status,
    q: str | None,
) -> tuple[list[KnowledgeDocumentListPublic], int]:
    repo = KnowledgeDocumentRepository(session)
    rows, total = await repo.list_in_store(
        store_id,
        page=page,
        page_size=page_size,
        sort=sort,
        direction=direction,
        document_type=document_type,
        processing_status=processing_status,
        q=q,
    )
    return [KnowledgeDocumentListPublic.from_model(row) for row in rows], total


async def get_knowledge_document(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    document_id: uuid.UUID,
) -> KnowledgeDocumentPublic:
    repo = KnowledgeDocumentRepository(session)
    document = await repo.get_in_store(store_id, document_id)
    if document is None:
        raise AppError("Document not found", code="not_found", status_code=404)
    return KnowledgeDocumentPublic.from_model(document, include_full_text=True)


async def delete_knowledge_document(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    repo = KnowledgeDocumentRepository(session)
    document = await repo.get_in_store(store_id, document_id)
    if document is None:
        raise AppError("Document not found", code="not_found", status_code=404)
    root = _storage_root()
    try:
        path = resolve_storage_path(root, document.storage_key)
        if path.is_file():
            path.unlink()
        parent = path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    except AppError:
        logger.warning("knowledge_delete_storage_skipped document_id=%s", document_id)
    import asyncio

    from app.services.rag.chroma_store import delete_document_chunks

    await asyncio.to_thread(delete_document_chunks, store_id, document_id)
    await session.delete(document)
    await session.commit()


async def reprocess_knowledge_document(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    document_id: uuid.UUID,
) -> KnowledgeDocumentPublic:
    repo = KnowledgeDocumentRepository(session)
    document = await repo.get_in_store(store_id, document_id)
    if document is None:
        raise AppError("Document not found", code="not_found", status_code=404)
    document.processing_status = KnowledgeProcessingStatus.UPLOADED
    document.page_count = None
    document.extracted_text = None
    document.error_message = None
    await session.commit()
    await session.refresh(document)
    schedule_document_processing(document_id)
    return KnowledgeDocumentPublic.from_model(document)


def extract_text(content: bytes, ext: str) -> ExtractionResult:
    """Processing entry point (patched in tests)."""

    return _extract_text(content, ext)


def schedule_document_processing(document_id: uuid.UUID) -> None:
    task = asyncio.create_task(_run_processing_job(document_id))
    _processing_tasks.add(task)
    task.add_done_callback(_processing_tasks.discard)


async def _run_processing_job(document_id: uuid.UUID) -> None:
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        document = await session.get(StoreKnowledgeDocument, document_id)
        if document is None:
            return
        if document.processing_status not in (
            KnowledgeProcessingStatus.UPLOADED,
            KnowledgeProcessingStatus.FAILED,
        ):
            return
        document.processing_status = KnowledgeProcessingStatus.PROCESSING
        document.error_message = None
        await session.commit()

        try:
            root = Path(settings.knowledge_storage_path)
            path = resolve_storage_path(root, document.storage_key)
            content = path.read_bytes()
            ext = extension_for_filename(document.original_filename)
            validate_file_content(content, ext)
            result: ExtractionResult = extract_text(content, ext)
            if not result.text:
                raise ValueError("No extractable text was found in the document")
            document.extracted_text = result.text
            document.page_count = result.page_count
            document.processing_status = KnowledgeProcessingStatus.PROCESSED
            document.error_message = None
        except Exception as exc:  # noqa: BLE001 — job boundary
            logger.exception("knowledge_processing_failed document_id=%s", document_id)
            document.processing_status = KnowledgeProcessingStatus.FAILED
            document.extracted_text = None
            document.page_count = None
            document.error_message = sanitize_processing_error(str(exc))
        await session.commit()