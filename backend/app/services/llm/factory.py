"""Select the configured policy LLM provider."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.llm.base import PolicyLLM
from app.services.llm.gemini_provider import GeminiPolicyLLM
from app.services.llm.mock_provider import MockPolicyLLM


def get_policy_llm(settings: Settings | None = None) -> PolicyLLM:
    cfg = settings or get_settings()
    if cfg.llm_provider == "gemini":
        return GeminiPolicyLLM(api_key=cfg.gemini_api_key, model=cfg.gemini_model)
    return MockPolicyLLM()