"""LLM abstraction for grounded policy answers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PolicyLLMRequest:
    system_prompt: str
    user_prompt: str
    question: str


@dataclass(frozen=True)
class PolicyLLMResponse:
    answer: str
    model: str


class PolicyLLM(Protocol):
    def generate(self, request: PolicyLLMRequest) -> PolicyLLMResponse: ...