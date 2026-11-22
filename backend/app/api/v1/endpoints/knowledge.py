"""Store knowledge documents."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_permission
from app.core.knowledge_enums import KnowledgeDocumentType, KnowledgeProcessingStatus
from app.core.permissions import Permission
from app.core.responses import success_body
from app.schemas.knowledge import KnowledgeDocumentPublic
from app.schemas.pagination import Paginated
from app.services.knowledge import (
    delete_knowledge_document,
    get_knowledge_document,
    list_knowledge_documents,
    reprocess_knowledge_document,
    upload_knowledge_document,
)

router = APIRouter(prefix="/stores/current/knowledge/documents")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("", summary="List knowledge documents")
async def list_documents(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("uploaded_at"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    document_type: KnowledgeDocumentType | None = None,
    processing_status: KnowledgeProcessingStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
) -> JSONResponse:
    items, total = await list_knowledge_documents(
        session,
        store_id=context.store.id,
        page=page,
        page_size=page_size,
        sort=sort,
        direction=direction,
        document_type=document_type,
        processing_status=processing_status,
        q=q,
    )
    body = Paginated(items=items, page=page, page_size=page_size, total=total)
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.post("", summary="Upload a knowledge document", status_code=201)
async def upload_document(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    document_type: KnowledgeDocumentType = Form(KnowledgeDocumentType.RETURN_POLICY),
) -> JSONResponse:
    raw = await file.read()
    created = await upload_knowledge_document(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        filename=file.filename or "document",
        content=raw,
        document_type=document_type,
    )
    return JSONResponse(status_code=201, content=success_body(created, _request_id(request)))


@router.get("/{document_id}", summary="Knowledge document detail")
async def document_detail(
    request: Request,
    document_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body: KnowledgeDocumentPublic = await get_knowledge_document(
        session,
        store_id=context.store.id,
        document_id=document_id,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))


@router.delete("/{document_id}", summary="Delete a knowledge document")
async def remove_document(
    request: Request,
    document_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await delete_knowledge_document(session, store_id=context.store.id, document_id=document_id)
    return JSONResponse(content=success_body({"deleted": True, "id": str(document_id)}, _request_id(request)))


@router.post("/{document_id}/reprocess", summary="Re-run text extraction")
async def reprocess_document(
    request: Request,
    document_id: uuid.UUID,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body = await reprocess_knowledge_document(
        session,
        store_id=context.store.id,
        document_id=document_id,
    )
    return JSONResponse(content=success_body(body, _request_id(request)))