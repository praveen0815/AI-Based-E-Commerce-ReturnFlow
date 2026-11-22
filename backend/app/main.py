"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.responses import success_body
from app.database.redis import close_redis, init_redis
from app.database.session import dispose_engine, init_engine
from app.middleware import RequestContextMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and clients, then release them on shutdown."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    init_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_timeout=settings.database_connect_timeout_seconds,
    )
    init_redis(settings.redis_url, connect_timeout=settings.redis_connect_timeout_seconds)
    if settings.is_production and "change-me" in settings.database_url:
        logger.warning("database_url_uses_placeholder_password")
    if len(settings.jwt_secret) < 32:
        logger.warning("jwt_secret_missing_or_short")
    logger.info("application_started env=%s version=%s", settings.app_env, __version__)
    try:
        yield
    finally:
        await close_redis()
        await dispose_engine()
        logger.info("application_stopped")


def create_app() -> FastAPI:
    """Build the API application."""

    settings = get_settings()
    docs_url = None if settings.is_production else "/api/docs"
    redoc_url = None if settings.is_production else "/api/redoc"
    openapi_url = None if settings.is_production else "/api/openapi.json"

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="ReturnFlow API foundation",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Store-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root(request: Request) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        return JSONResponse(
            content=success_body(
                {
                    "service": settings.app_name,
                    "version": __version__,
                    "health": f"{settings.api_v1_prefix}/health",
                    "ready": f"{settings.api_v1_prefix}/ready",
                    "docs": docs_url or "",
                },
                request_id,
            )
        )

    return app


app = create_app()
