"""ChromaDB persistence with per-store collections."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings

_client_lock = threading.Lock()
_client: chromadb.PersistentClient | None = None


def _collection_name(store_id: uuid.UUID) -> str:
    return f"knowledge_{store_id.hex}"


def _client_instance() -> chromadb.PersistentClient:
    global _client
    with _client_lock:
        if _client is None:
            settings = get_settings()
            _client = chromadb.PersistentClient(path=settings.chroma_persist_path)
        return _client


def get_store_collection(store_id: uuid.UUID) -> Collection:
    client = _client_instance()
    return client.get_or_create_collection(
        name=_collection_name(store_id),
        metadata={"hnsw:space": "cosine"},
    )


def reset_client_for_tests() -> None:
    global _client
    with _client_lock:
        _client = None


@dataclass(frozen=True)
class StoredChunkHit:
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]


def upsert_chunks(
    store_id: uuid.UUID,
    *,
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
) -> None:
    collection = get_store_collection(store_id)
    collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def delete_document_chunks(store_id: uuid.UUID, document_id: uuid.UUID) -> None:
    collection = get_store_collection(store_id)
    collection.delete(where={"document_id": str(document_id)})


def delete_store_index(store_id: uuid.UUID) -> None:
    client = _client_instance()
    name = _collection_name(store_id)
    try:
        client.delete_collection(name)
    except ValueError:
        return


def query_chunks(
    store_id: uuid.UUID,
    *,
    query_embedding: list[float],
    top_k: int,
) -> list[StoredChunkHit]:
    collection = get_store_collection(store_id)
    if collection.count() == 0:
        return []
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    hits: list[StoredChunkHit] = []
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    for chunk_id, doc, meta, distance in zip(ids, documents, metadatas, distances, strict=True):
        score = max(0.0, 1.0 - float(distance))
        hits.append(
            StoredChunkHit(
                chunk_id=chunk_id,
                text=doc or "",
                score=score,
                metadata=meta or {},
            )
        )
    return hits