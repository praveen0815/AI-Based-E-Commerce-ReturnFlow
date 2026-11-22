"""Semantic retrieval and context assembly."""

from __future__ import annotations

import asyncio
import uuid

from app.core.config import get_settings
from app.services.rag.chroma_store import StoredChunkHit, query_chunks
from app.services.rag.embeddings import get_embeddings_provider


def assemble_context(hits: list[StoredChunkHit]) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        meta = hit.metadata
        filename = meta.get("original_filename", "document")
        section = meta.get("section_label", "section")
        page = meta.get("page_hint") or "n/a"
        blocks.append(
            f"[Source {index}] file={filename} section={section} page={page} score={hit.score:.2f}\n{hit.text}"
        )
    return "\n\n".join(blocks)


async def search_knowledge(
    store_id: uuid.UUID,
    *,
    query: str,
    top_k: int | None = None,
) -> list[StoredChunkHit]:
    settings = get_settings()
    limit = top_k or settings.rag_top_k
    provider = get_embeddings_provider(settings)
    embedding = await asyncio.to_thread(provider.embed_query, query)
    hits = await asyncio.to_thread(query_chunks, store_id, query_embedding=embedding, top_k=limit)
    return [hit for hit in hits if hit.score >= settings.rag_min_relevance_score]


def hits_to_citations(hits: list[StoredChunkHit]) -> list[dict]:
    citations: list[dict] = []
    for index, hit in enumerate(hits, start=1):
        meta = hit.metadata
        citations.append(
            {
                "label": f"Source {index}",
                "document_id": meta.get("document_id"),
                "original_filename": meta.get("original_filename"),
                "document_type": meta.get("document_type"),
                "section_label": meta.get("section_label"),
                "page_hint": meta.get("page_hint") or None,
                "chunk_index": meta.get("chunk_index"),
                "score": round(hit.score, 4),
                "excerpt": hit.text[:320],
            }
        )
    return citations