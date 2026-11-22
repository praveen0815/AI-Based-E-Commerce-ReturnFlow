"""RAG indexing, search, and policy assistant."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_permission
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.core.responses import success_body
from app.repositories.knowledge import KnowledgeDocumentRepository
from app.schemas.knowledge import KnowledgeDocumentPublic
from app.schemas.rag import PolicyFeedbackRequest, RagAskRequest, RagIndexRequest, RagSearchRequest
from app.services.rag.indexing import delete_index, index_document, reindex_store
from app.services.rag.policy_chat import ask_policy_question, save_policy_feedback
from app.services.rag.retrieval import hits_to_citations, search_knowledge

router = APIRouter(prefix="/stores/current/knowledge/rag")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.post("/index", summary="Index processed knowledge documents")
async def index_knowledge(
    request: Request,
    body: RagIndexRequest,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if body.document_id is None:
        summary = await reindex_store(session, store_id=context.store.id)
        return JSONResponse(content=success_body(summary, _request_id(request)))
    document = await index_document(session, store_id=context.store.id, document_id=body.document_id)
    public = KnowledgeDocumentPublic.from_model(document)
    return JSONResponse(content=success_body(public, _request_id(request)))


@router.post("/reindex", summary="Reindex all processed documents for the store")
async def reindex_knowledge(
    request: Request,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    summary = await reindex_store(session, store_id=context.store.id)
    return JSONResponse(content=success_body(summary, _request_id(request)))


@router.delete("/index", summary="Delete vector index for the store or one document")
async def delete_knowledge_index(
    request: Request,
    document_id: uuid.UUID | None = None,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await delete_index(session, store_id=context.store.id, document_id=document_id)
    return JSONResponse(content=success_body(result, _request_id(request)))


@router.post("/search", summary="Semantic search over indexed policy text")
async def search_policy_knowledge(
    request: Request,
    body: RagSearchRequest,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
) -> JSONResponse:
    hits = await search_knowledge(context.store.id, query=body.query, top_k=body.top_k)
    payload = {
        "hits": [
            {
                "chunk_id": hit.chunk_id,
                "score": round(hit.score, 4),
                "text": hit.text,
                "citation": hits_to_citations([hit])[0],
            }
            for hit in hits
        ],
        "total": len(hits),
    }
    return JSONResponse(content=success_body(payload, _request_id(request)))


@router.post("/ask", summary="Ask a grounded policy question")
async def ask_policy(
    request: Request,
    body: RagAskRequest,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
) -> JSONResponse:
    result = await ask_policy_question(context.store.id, question=body.question, top_k=body.top_k)
    return JSONResponse(content=success_body(result, _request_id(request)))


@router.get("/sources", summary="Retrieve source document summaries for citations")
async def list_sources(
    request: Request,
    document_id: uuid.UUID | None = None,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    repo = KnowledgeDocumentRepository(session)
    if document_id is not None:
        document = await repo.get_in_store(context.store.id, document_id)
        if document is None:
            raise AppError("Document not found", code="not_found", status_code=404)
        items = [KnowledgeDocumentPublic.from_model(document, include_full_text=False)]
    else:
        rows, _ = await repo.list_in_store(
            context.store.id,
            page=1,
            page_size=100,
            sort="uploaded_at",
            direction="desc",
            document_type=None,
            processing_status=None,
            q=None,
        )
        items = [KnowledgeDocumentPublic.from_model(row, include_full_text=False) for row in rows]
    return JSONResponse(content=success_body({"sources": items}, _request_id(request)))


@router.post("/feedback", summary="Submit policy assistant feedback", status_code=201)
async def policy_feedback(
    request: Request,
    body: PolicyFeedbackRequest,
    context: StoreContext = Depends(require_permission(Permission.KNOWLEDGE_READ)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await save_policy_feedback(
        session,
        store_id=context.store.id,
        user_id=context.user.id,
        helpful=body.helpful,
        question=body.question,
        answer_excerpt=body.answer_excerpt,
    )
    return JSONResponse(status_code=201, content=success_body({"saved": True}, _request_id(request)))