"""Optional live Gemini smoke test — skipped without credentials."""

from __future__ import annotations

import os

import pytest

from app.core.config import get_settings
from app.services.llm.factory import get_policy_llm
from app.services.llm.base import PolicyLLMRequest
from app.services.rag.prompts import SYSTEM_PROMPT, build_user_prompt


@pytest.mark.live_llm
def test_gemini_policy_smoke() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        pytest.skip("GEMINI_API_KEY is not set")

    os.environ["LLM_PROVIDER"] = "gemini"
    get_settings.cache_clear()
    llm = get_policy_llm()
    response = llm.generate(
        PolicyLLMRequest(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                question="Can I return after 30 days?",
                context_block="[Source 1] file=policy.txt section=Section 1 page=n/a score=0.90\nReturns within 30 days.",
            ),
            question="Can I return after 30 days?",
        )
    )
    assert response.answer
    assert "gemini" in response.model