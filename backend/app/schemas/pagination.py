"""List pagination query parameters and envelopes."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int