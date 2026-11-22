"""Natural-language explanation layer — cannot change eligibility."""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.eligibility_enums import EligibilityDecision
from app.services.llm.base import PolicyLLMRequest
from app.services.llm.factory import get_policy_llm
from app.services.rag.prompts import sanitize_user_question
from app.services.rag.retrieval import assemble_context, hits_to_citations, search_knowledge


EXPLAIN_SYSTEM = """You assist support staff by explaining a FINAL eligibility decision.
The decision and code are authoritative and must not be changed, reversed, or overridden.
You may clarify the customer reason, summarize evidence, list missing information, and suggest next steps.
Do not invent refund policies, amounts, or approvals."""


async def build_ai_explanation(
    *,
    store_id,
    decision: EligibilityDecision,
    decision_code: str,
    explanation: str,
    reason: str,
    description: str,
    missing_information: list,
    recommended_next_steps: list,
    policy_citations: list | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    hits = await search_knowledge(store_id, query=sanitize_user_question(f"{reason} {description}")[:400], top_k=3)
    context = assemble_context(hits) if hits else "(No indexed policy excerpts found.)"
    citation_lines = hits_to_citations(hits) if hits else policy_citations or []

    user_prompt = (
        f"FINAL DECISION: {decision.value} ({decision_code})\n"
        f"DETERMINISTIC EXPLANATION: {explanation}\n"
        f"CUSTOMER REASON: {reason}\n"
        f"CUSTOMER DESCRIPTION: {description}\n"
        f"MISSING INFORMATION: {missing_information}\n"
        f"NEXT STEPS: {recommended_next_steps}\n"
        f"KNOWLEDGE EXCERPTS:\n{context}\n"
        f"CITATIONS: {citation_lines}\n"
        "Write a short staff-facing summary (3-6 sentences)."
    )
    llm = get_policy_llm(settings)
    response = await asyncio.to_thread(
        llm.generate,
        PolicyLLMRequest(system_prompt=EXPLAIN_SYSTEM, user_prompt=user_prompt, question=reason),
    )
    return response.answer, response.model