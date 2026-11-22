"""Eligibility evaluation API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.eligibility_enums import EligibilityDecision
from app.core.return_lifecycle import RequestedResolution


class EligibilityLineInput(BaseModel):
    order_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)
    condition: str | None = Field(default=None, max_length=32)


class EligibilityEvaluateRequest(BaseModel):
    order_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    requested_resolution: RequestedResolution
    items: list[EligibilityLineInput]
    return_request_id: uuid.UUID | None = None
    customer_user_id: uuid.UUID | None = None
    include_ai_explanation: bool = False


class EligibilityDecisionPublic(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    order_id: uuid.UUID
    return_request_id: uuid.UUID | None
    decision: EligibilityDecision
    decision_code: str
    explanation: str
    decision_reason: str
    policy_rule_version: int
    policy_references: list[dict[str, Any]]
    missing_information: list[dict[str, Any]]
    recommended_next_steps: list[str]
    ai_explanation: str | None
    ai_model: str | None
    human_review_requested: bool
    evaluated_at: datetime

    @classmethod
    def from_model(cls, row) -> "EligibilityDecisionPublic":
        return cls(
            id=row.id,
            store_id=row.store_id,
            order_id=row.order_id,
            return_request_id=row.return_request_id,
            decision=row.decision,
            decision_code=row.decision_code,
            explanation=row.explanation,
            decision_reason=row.decision_reason,
            policy_rule_version=row.policy_rule_version,
            policy_references=row.policy_references,
            missing_information=row.missing_information,
            recommended_next_steps=row.recommended_next_steps,
            ai_explanation=row.ai_explanation,
            ai_model=row.ai_model,
            human_review_requested=row.human_review_requested,
            evaluated_at=row.evaluated_at,
        )