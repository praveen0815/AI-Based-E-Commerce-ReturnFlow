"""Deterministic LLM for tests and offline development."""

from __future__ import annotations

from app.services.llm.base import PolicyLLMRequest, PolicyLLMResponse


class MockPolicyLLM:
    def generate(self, request: PolicyLLMRequest) -> PolicyLLMResponse:
        excerpt = request.user_prompt[:280].replace("\n", " ")
        answer = (
            "Based on the store policy excerpts provided, here is a grounded summary. "
            f"Regarding your question ({request.question!r}): {excerpt}"
        )
        return PolicyLLMResponse(answer=answer, model="mock-policy-llm")