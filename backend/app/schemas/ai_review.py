"""AI review workflow API and agent output schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IntakeAgentOutput(BaseModel):
    summary: str = Field(max_length=2000)
    extracted_reason: str = Field(max_length=200)
    requested_resolution: str = Field(max_length=32)
    missing_information: list[str] = Field(default_factory=list, max_length=20)


class PolicyResearchOutput(BaseModel):
    evidence_summary: str = Field(max_length=4000)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    policy_gaps: list[str] = Field(default_factory=list)


class EligibilityAgentOutput(BaseModel):
    decision_id: uuid.UUID | None = None
    decision: str
    decision_code: str
    explanation: str
    policy_references: list[dict[str, Any]] = Field(default_factory=list)
    locked: bool = True


class ResolutionAgentOutput(BaseModel):
    suggested_resolution: Literal["REFUND", "EXCHANGE", "STORE_CREDIT", "NONE", "NEEDS_REVIEW"]
    rationale: str = Field(max_length=2000)
    customer_message: str = Field(max_length=2000)


class ReviewAgentOutput(BaseModel):
    consistent: bool
    issues: list[str] = Field(default_factory=list)
    request_revision: bool = False
    revision_target: Literal["POLICY_RESEARCH", "NONE"] = "NONE"


class FinalizationOutput(BaseModel):
    recommendation: Literal["APPROVE_FOR_PROCESSING", "DENY", "ESCALATE_HUMAN"]
    summary: str = Field(max_length=4000)
    next_steps: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True


class AiReviewStartResponse(BaseModel):
    run_id: uuid.UUID
    status: str


class AiReviewRunPublic(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    return_request_id: uuid.UUID
    status: str
    current_agent: str | None
    revision_count: int
    output_payload: dict[str, Any] | None
    error_message: str | None
    human_decision: str | None
    human_note: str | None
    started_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, row) -> "AiReviewRunPublic":
        return cls(
            id=row.id,
            store_id=row.store_id,
            return_request_id=row.return_request_id,
            status=row.status.value,
            current_agent=row.current_agent,
            revision_count=row.revision_count,
            output_payload=row.output_payload,
            error_message=row.error_message,
            human_decision=row.human_decision,
            human_note=row.human_note,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )


class AiReviewEventPublic(BaseModel):
    id: uuid.UUID
    sequence: int
    agent: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_model(cls, row) -> "AiReviewEventPublic":
        return cls(
            id=row.id,
            sequence=row.sequence,
            agent=row.agent,
            event_type=row.event_type,
            payload=row.payload,
            created_at=row.created_at,
        )


class AiReviewResumeRequest(BaseModel):
    decision: Literal["ACKNOWLEDGE", "OVERRULE_RECOMMENDATION"]
    note: str | None = Field(default=None, max_length=500)