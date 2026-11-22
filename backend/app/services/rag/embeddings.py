"""Embedding providers for semantic search."""

from __future__ import annotations

import hashlib
import math
import threading
from abc import ABC, abstractmethod

from app.core.config import Settings, get_settings

_DIM = 384
_model_lock = threading.Lock()
_sentence_model = None


class EmbeddingsProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddings(EmbeddingsProvider):
    """Deterministic vectors for tests without loading transformer weights."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_vector_for(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return _vector_for(text)


def _vector_for(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(_DIM)]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class SentenceTransformerEmbeddings(EmbeddingsProvider):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    def _model(self):
        global _sentence_model
        with _model_lock:
            if _sentence_model is None:
                from sentence_transformers import SentenceTransformer

                _sentence_model = SentenceTransformer(self._model_name)
            return _sentence_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_embeddings_provider(settings: Settings | None = None) -> EmbeddingsProvider:
    cfg = settings or get_settings()
    if cfg.rag_embeddings_provider == "mock":
        return MockEmbeddings()
    return SentenceTransformerEmbeddings(cfg.rag_embedding_model)