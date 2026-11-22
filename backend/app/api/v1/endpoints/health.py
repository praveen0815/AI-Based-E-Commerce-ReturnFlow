"""Liveness and readiness endpoints."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.responses import error_body, success_body
from app.database.redis import get_redis
from app.database.session import get_session_factory
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.health import HealthData, ReadinessChecks, ReadinessData
from app.services.health import check_database, check_redis

logger = logging.getLogger(__name__)
router = APIRouter()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get(
    "/health",
    summary="Liveness probe",
    responses={200: {"model": SuccessResponse[HealthData]}},
)
async def health(request: Request) -> JSONResponse:
    """Report that the API process is running. This does not check dependencies."""

    settings = get_settings()
    payload = HealthData(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=__version__,
    )
    return JSONResponse(
        status_code=200,
        content=success_body(payload, _request_id(request)),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    responses={
        200: {"model": SuccessResponse[ReadinessData]},
        503: {"model": ErrorResponse},
    },
)
async def ready(request: Request) -> JSONResponse:
    """Report whether PostgreSQL and Redis accepted a connectivity check."""

    settings = get_settings()
    request_id = _request_id(request)
    database = await check_database(get_session_factory(), settings.health_check_timeout_seconds)
    redis = await check_redis(get_redis(), settings.health_check_timeout_seconds)
    checks = ReadinessChecks(database=database, redis=redis)
    is_ready = database.status == "up" and redis.status == "up"
    payload = ReadinessData(status="ready" if is_ready else "not_ready", checks=checks)

    if is_ready:
        return JSONResponse(status_code=200, content=success_body(payload, request_id))

    logger.warning(
        "readiness_failed database=%s redis=%s",
        database.status,
        redis.status,
    )
    return JSONResponse(
        status_code=503,
        content=error_body(
            "not_ready",
            "One or more dependencies are unavailable",
            request_id,
            payload.model_dump(exclude_none=True),
        ),
    )
