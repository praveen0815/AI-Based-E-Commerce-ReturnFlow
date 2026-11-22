"""Health and readiness payloads."""

from typing import Literal

from pydantic import BaseModel


class HealthData(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    version: str


class DependencyCheck(BaseModel):
    status: Literal["up", "down"]
    detail: str | None = None


class ReadinessChecks(BaseModel):
    database: DependencyCheck
    redis: DependencyCheck


class ReadinessData(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks
