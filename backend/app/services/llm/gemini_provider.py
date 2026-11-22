"""Google Gemini policy LLM."""

from __future__ import annotations

from app.core.exceptions import AppError
from app.services.llm.base import PolicyLLMRequest, PolicyLLMResponse


class GeminiPolicyLLM:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key.strip():
            raise AppError("Gemini is not configured", code="llm_not_configured", status_code=503)
        self._api_key = api_key
        self._model = model

    def generate(self, request: PolicyLLMRequest) -> PolicyLLMResponse:
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            self._model,
            system_instruction=request.system_prompt,
        )
        response = model.generate_content(request.user_prompt)
        text = (response.text or "").strip()
        if not text:
            raise AppError("The model returned an empty answer", code="llm_empty", status_code=502)
        return PolicyLLMResponse(answer=text, model=self._model)