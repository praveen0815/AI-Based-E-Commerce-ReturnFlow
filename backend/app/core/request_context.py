"""Request id normalization shared by middleware and tests."""

from __future__ import annotations

import uuid

_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


def normalize_request_id(value: str | None) -> str:
    """Keep a caller-supplied id when it is safe, otherwise generate one."""

    if not value:
        return str(uuid.uuid4())
    cleaned = "".join(character for character in value.strip() if character in _ALLOWED)
    return cleaned[:128] or str(uuid.uuid4())
