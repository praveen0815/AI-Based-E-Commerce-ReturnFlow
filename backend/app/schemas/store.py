"""Store and membership payloads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.permissions import MemberRole


class StoreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Store name must be at least 2 characters")
        return cleaned


class StoreUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Store name must be at least 2 characters")
        return cleaned


class StorePublic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: MemberRole


class MemberCreate(BaseModel):
    email: EmailStr
    role: MemberRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class MemberUpdate(BaseModel):
    role: MemberRole


class MemberPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: MemberRole
