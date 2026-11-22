"""Structured logging."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, RequestIdFilter, configure_logging, request_id_ctx
from app.core.request_context import normalize_request_id


def test_json_formatter_includes_the_request_id() -> None:
    token = request_id_ctx.set("req-json")
    try:
        record = logging.LogRecord(
            name="returnflow.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="application_started",
            args=(),
            exc_info=None,
        )
        assert RequestIdFilter().filter(record) is True
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)

    assert payload["message"] == "application_started"
    assert payload["request_id"] == "req-json"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "returnflow.test"


def test_plain_formatter_is_configured_without_json(capsys: object) -> None:
    configure_logging("INFO", json_logs=False)
    logging.getLogger("returnflow.test").info("plain_log")
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "plain_log" in captured.out
    assert "INFO" in captured.out


def test_request_id_falls_back_when_missing_or_empty() -> None:
    generated = normalize_request_id(None)
    assert generated
    assert normalize_request_id("   ") != "   "
    assert normalize_request_id("ok.id_1") == "ok.id_1"
    assert len(normalize_request_id("a" * 200)) == 128
