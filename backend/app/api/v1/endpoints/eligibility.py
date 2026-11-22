"""Return eligibility and policy rules."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StoreContext, get_db, require_any_store_permission, require_permission
from app.core.permissions import Permission
from app.core.responses import success_body
from app.schemas.eligibility import EligibilityEvaluateRequest
from app.schemas.policy_rules import StorePolicyRulesConfig
from app.services.eligibility.policy_rules_service import get_active_policy_rules, publish_policy_rules
from app.services.eligibility.service import (
    evaluate_return_eligibility,
    explain_eligibility_decision,
    get_eligibility_decision,
    latest_for_return,
    request_human_review,
)

router = APIRouter(prefix="/stores/current/returns")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/eligibility/evaluate", summary="Evaluate return eligibility")
async def evaluate_eligibility(
    request: Request,
    body: EligibilityEvaluateRequest,
    context: StoreContext = Depends(
        require_any_store_permission(
            Permission.RETURN_CREATE,
            Permission.RETURN_READ,
            Permission.RETURN_MANAGE,
        )
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    decision = await evaluate_return_eligibility(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        payload=body,
        ip_address=_client_ip(request),
        include_ai=body.include_ai_explanation,
    )
    return JSONResponse(content=success_body(decision, _request_id(request)))


@router.get("/eligibility/{decision_id}", summary="Eligibility decision detail")
async def eligibility_detail(
    request: Request,
    decision_id: uuid.UUID,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN, Permission.RETURN_MANAGE)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    decision = await get_eligibility_decision(
        session,
        store_id=context.store.id,
        decision_id=decision_id,
        role=context.membership.role,
        actor_id=context.user.id,
    )
    return JSONResponse(content=success_body(decision, _request_id(request)))


@router.post("/eligibility/{decision_id}/explain", summary="Generate AI explanation for a decision")
async def eligibility_explain(
    request: Request,
    decision_id: uuid.UUID,
    context: StoreContext = Depends(require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    decision = await explain_eligibility_decision(
        session,
        store_id=context.store.id,
        decision_id=decision_id,
        role=context.membership.role,
    )
    return JSONResponse(content=success_body(decision, _request_id(request)))


@router.post("/eligibility/{decision_id}/request-review", summary="Request human review")
async def eligibility_request_review(
    request: Request,
    decision_id: uuid.UUID,
    context: StoreContext = Depends(require_any_store_permission(Permission.RETURN_CREATE, Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    decision = await request_human_review(
        session,
        store_id=context.store.id,
        decision_id=decision_id,
        actor_id=context.user.id,
        role=context.membership.role,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body(decision, _request_id(request)))


@router.get("/policy-rules", summary="Active return policy rules")
async def policy_rules_get(
    request: Request,
    context: StoreContext = Depends(require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    config, version, row_id = await get_active_policy_rules(session, context.store.id)
    return JSONResponse(
        content=success_body({"version": version, "id": str(row_id), "rules": config.model_dump()}, _request_id(request))
    )


@router.put("/policy-rules", summary="Publish new policy rule version")
async def policy_rules_put(
    request: Request,
    body: StorePolicyRulesConfig,
    context: StoreContext = Depends(require_permission(Permission.RETURN_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    config, version = await publish_policy_rules(
        session,
        store_id=context.store.id,
        actor_id=context.user.id,
        role=context.membership.role,
        config=body,
        ip_address=_client_ip(request),
    )
    return JSONResponse(content=success_body({"version": version, "rules": config.model_dump()}, _request_id(request)))


@router.get("/{return_id}/eligibility", summary="Latest eligibility for a return")
async def return_eligibility_latest(
    request: Request,
    return_id: uuid.UUID,
    context: StoreContext = Depends(
        require_any_store_permission(Permission.RETURN_READ, Permission.RETURN_READ_OWN, Permission.RETURN_MANAGE)
    ),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    decision = await latest_for_return(
        session,
        store_id=context.store.id,
        return_id=return_id,
        role=context.membership.role,
        actor_id=context.user.id,
    )
    return JSONResponse(content=success_body({"decision": decision}, _request_id(request)))