"""Grounded policy Q&A."""

from __future__ import annotations

import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.policy_feedback import PolicyChatFeedback
from app.services.llm.factory import get_policy_llm
from app.services.llm.base import PolicyLLMRequest
from app.services.rag.prompts import SYSTEM_PROMPT, build_user_prompt, sanitize_user_question
from app.services.rag.retrieval import assemble_context, hits_to_citations, search_knowledge


UNCERTAIN_MESSAGE = (
    "I could not find enough matching policy text in this store's knowledge base to answer confidently. "
    "Upload or re-index return policy documents, then try again."
)


async def ask_policy_question(
    store_id: uuid.UUID,
    *,
    question: str,
    top_k: int | None = None,
) -> dict:
    cleaned = sanitize_user_question(question)
    if len(cleaned) < 3:
        raise AppError("Ask a longer policy question", code="invalid_question", status_code=400)

    hits = await search_knowledge(store_id, query=cleaned, top_k=top_k)
    citations = hits_to_citations(hits)
    if not hits:
        return {
            "answer": UNCERTAIN_MESSAGE,
            "grounded": False,
            "model": "n/a",
            "citations": [],
            "retrieval_count": 0,
        }

    context_block = assemble_context(hits)
    user_prompt = build_user_prompt(question=cleaned, context_block=context_block)
    settings = get_settings()
    llm = get_policy_llm(settings)
    response = await asyncio.to_thread(
        llm.generate,
        PolicyLLMRequest(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, question=cleaned),
    )
    return {
        "answer": response.answer,
        "grounded": True,
        "model": response.model,
        "citations": citations,
        "retrieval_count": len(hits),
    }


async def save_policy_feedback(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    helpful: bool,
    question: str,
    answer_excerpt: str | None,
) -> None:
    row = PolicyChatFeedback(
        store_id=store_id,
        user_id=user_id,
        helpful=helpful,
        question=sanitize_user_question(question, max_length=500),
        answer_excerpt=(answer_excerpt or "")[:500] or None,
    )
    session.add(row)
    await session.commit()