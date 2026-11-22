"""Helpers for the public API envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def dump_data(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json", exclude_none=True)
    if isinstance(data, dict):
        return {str(key): dump_data(value) for key, value in data.items()}
    if isinstance(data, list):
        return [dump_data(item) for item in data]
    return data


def success_body(
    data: BaseModel | dict[str, Any],
    request_id: str,
    message: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "success": True,
        "data": dump_data(data),
        "request_id": request_id,
    }
    if message is not None:
        body["message"] = message
    return body


def error_body(
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"success": False, "error": error, "request_id": request_id}
