"""AI return review workflow statuses."""

from enum import Enum


class AiReviewRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class AiReviewAgent(str, Enum):
    INTAKE = "INTAKE"
    POLICY_RESEARCH = "POLICY_RESEARCH"
    ELIGIBILITY = "ELIGIBILITY"
    RESOLUTION = "RESOLUTION"
    REVIEW = "REVIEW"
    FINALIZATION = "FINALIZATION"