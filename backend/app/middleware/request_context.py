"""ASGI middleware that assigns a request id and writes an access log."""

from __future__ import annotations

import logging
import time

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx
from app.core.request_context import normalize_request_id

logger = logging.getLogger("returnflow.access")


class RequestContextMiddleware:
    """Outermost HTTP middleware for correlation and access logging.

    Query strings are intentionally omitted so tokens do not land in logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = normalize_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request_completed method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
            request_id_ctx.reset(token)
