"""Password hashing and access tokens.

Tokens are signed JWTs. They are accepted only while their id still exists
in Redis, so logout can invalidate a token before it expires.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.exceptions import AppError

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("returnflow-dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_password_or_dummy(password_hash: str | None, password: str) -> bool:
    """Spend a hash verification even when the account does not exist."""

    if password_hash is None:
        verify_password(_DUMMY_HASH, password)
        return False
    verified = verify_password(password_hash, password)
    return verified


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def session_key(token_id: str) -> str:
    return f"auth:session:{token_id}"


def create_access_token(*, user_id: uuid.UUID, secret: str, ttl_seconds: int) -> tuple[str, str, int]:
    if len(secret) < 32:
        raise AppError(
            "Authentication is not configured",
            code="auth_not_configured",
            status_code=500,
        )
    now = datetime.now(UTC)
    token_id = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, token_id, ttl_seconds


def decode_access_token(token: str, secret: str) -> dict[str, str | int]:
    if len(secret) < 32:
        raise AppError(
            "Authentication is not configured",
            code="auth_not_configured",
            status_code=500,
        )
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError("Your session expired", code="token_expired", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError("Authentication required", code="not_authenticated", status_code=401) from exc
    subject = payload.get("sub")
    token_id = payload.get("jti")
    if not isinstance(subject, str) or not isinstance(token_id, str):
        raise AppError("Authentication required", code="not_authenticated", status_code=401)
    return payload
