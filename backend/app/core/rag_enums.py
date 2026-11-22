"""RAG indexing lifecycle for knowledge documents."""

from enum import Enum


class KnowledgeIndexStatus(str, Enum):
    NOT_INDEXED = "NOT_INDEXED"
    INDEXING = "INDEXING"
    INDEXED = "INDEXED"
    INDEX_FAILED = "INDEX_FAILED"