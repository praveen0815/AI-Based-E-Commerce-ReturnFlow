"""Authentication payloads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator, model_validator

from app.core.permissions import MemberRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("display_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Display name must be at least 2 characters")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not 12 <= len(password) <= 128:
            raise ValueError("Password must be 12 to 128 characters")
        return value

    @model_validator(mode="after")
    def password_differs_from_email(self) -> RegisterRequest:
        if self.password.get_secret_value().casefold() == str(self.email).casefold():
            raise ValueError("Password must not match the email")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not password or len(password) > 128:
            raise ValueError("Password is invalid")
        return value


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("display_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Display name must be at least 2 characters")
        return cleaned


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool


class MembershipPublic(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    store_slug: str
    role: MemberRole
    permissions: list[str]


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResult(BaseModel):
    token: TokenData
    user: UserPublic


class CurrentUserData(BaseModel):
    user: UserPublic
    memberships: list[MembershipPublic]
