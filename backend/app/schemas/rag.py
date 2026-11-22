"""RAG and policy assistant payloads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RagIndexRequest(BaseModel):
    document_id: uuid.UUID | None = None


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)


class RagAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)


class RagCitation(BaseModel):
    label: str
    document_id: str | None
    original_filename: str | None
    document_type: str | None
    section_label: str | None
    page_hint: str | None
    chunk_index: int | None
    score: float
    excerpt: str


class RagSearchHit(BaseModel):
    chunk_id: str
    score: float
    text: str
    citation: RagCitation


class PolicyFeedbackRequest(BaseModel):
    helpful: bool
    question: str = Field(max_length=500)
    answer_excerpt: str | None = Field(default=None, max_length=500)