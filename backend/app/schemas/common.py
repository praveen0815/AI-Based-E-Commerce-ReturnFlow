"""Shared API envelope schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None
    request_id: str = Field(description="Correlation id for this request")
