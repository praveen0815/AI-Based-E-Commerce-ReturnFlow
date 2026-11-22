"""Evaluate eligibility, persist audit rows, optional AI explanation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eligibility_enums import EligibilityDecision
from app.core.exceptions import AppError
from app.core.permissions import MemberRole, Permission, has_permission
from app.models.return_eligibility_decision import ReturnEligibilityDecision
from app.repositories.eligibility import EligibilityDecisionRepository
from app.repositories.orders import OrderRepository
from app.repositories.returns import ReturnRepository
from app.schemas.eligibility import EligibilityEvaluateRequest, EligibilityDecisionPublic
from app.services.audit import record_audit
from app.services.eligibility.ai_explanation import build_ai_explanation
from app.services.eligibility.engine import EligibilityEvaluateInput, EligibilityItemInput, evaluate_eligibility
from app.services.eligibility.policy_rules_service import get_active_policy_rules


async def evaluate_return_eligibility(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    payload: EligibilityEvaluateRequest,
    ip_address: str | None,
    include_ai: bool = False,
) -> EligibilityDecisionPublic:
    if not (
        has_permission(role, Permission.RETURN_CREATE)
        or has_permission(role, Permission.RETURN_MANAGE)
        or has_permission(role, Permission.RETURN_READ)
    ):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)

    policy, policy_version, _ = await get_active_policy_rules(session, store_id)
    order = await OrderRepository(session).get_in_store(store_id, payload.order_id)
    order_items = {line.id: line for line in order.items} if order else {}
    returned_qty: dict[uuid.UUID, int] = {}
    if order:
        repo = ReturnRepository(session)
        for line in order.items:
            returned_qty[line.id] = await repo.returned_quantity(line.id)

    customer_id = payload.customer_user_id or (order.customer_user_id if order else actor_id)
    actor_is_customer = has_permission(role, Permission.RETURN_CREATE) and not has_permission(
        role, Permission.RETURN_MANAGE
    )

    engine_input = EligibilityEvaluateInput(
        order_id=payload.order_id,
        customer_user_id=customer_id,
        reason=payload.reason,
        description=payload.description,
        requested_resolution=payload.requested_resolution,
        items=[
            EligibilityItemInput(
                order_item_id=item.order_item_id,
                quantity=item.quantity,
                condition=item.condition,
            )
            for item in payload.items
        ],
    )
    outcome = evaluate_eligibility(
        order=order,
        order_items=order_items,
        returned_qty=returned_qty,
        policy=policy,
        policy_version=policy_version,
        payload=engine_input,
        actor_is_customer=actor_is_customer,
    )

    row = ReturnEligibilityDecision(
        store_id=store_id,
        order_id=payload.order_id,
        return_request_id=payload.return_request_id,
        customer_user_id=customer_id,
        actor_user_id=actor_id,
        decision=outcome.decision,
        decision_code=outcome.code.value,
        explanation=outcome.explanation,
        decision_reason=outcome.confidence.value,
        policy_rule_version=policy_version,
        policy_references=outcome.policy_references,
        missing_information=outcome.missing_information,
        recommended_next_steps=outcome.recommended_next_steps,
        request_snapshot=payload.model_dump(mode="json"),
        evaluated_at=datetime.now(UTC),
    )
    if include_ai:
        ai_text, ai_model = await build_ai_explanation(
            store_id=store_id,
            decision=outcome.decision,
            decision_code=outcome.code.value,
            explanation=outcome.explanation,
            reason=payload.reason,
            description=payload.description,
            missing_information=outcome.missing_information,
            recommended_next_steps=outcome.recommended_next_steps,
            policy_citations=outcome.policy_references,
        )
        row.ai_explanation = ai_text
        row.ai_model = ai_model

    EligibilityDecisionRepository(session).add(row)
    await record_audit(
        session,
        action="return.eligibility_evaluated",
        actor_user_id=actor_id,
        store_id=store_id,
        target_type="eligibility_decision",
        target_id=str(row.id),
        ip_address=ip_address,
        details={"decision": outcome.decision.value, "code": outcome.code.value},
    )
    await session.commit()
    await session.refresh(row)
    return EligibilityDecisionPublic.from_model(row)


async def get_eligibility_decision(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    decision_id: uuid.UUID,
    role: MemberRole,
    actor_id: uuid.UUID,
) -> EligibilityDecisionPublic:
    if not (
        has_permission(role, Permission.RETURN_READ)
        or has_permission(role, Permission.RETURN_READ_OWN)
        or has_permission(role, Permission.RETURN_MANAGE)
    ):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    row = await EligibilityDecisionRepository(session).get_in_store(store_id, decision_id)
    if row is None:
        raise AppError("Eligibility decision not found", code="not_found", status_code=404)
    if has_permission(role, Permission.RETURN_READ_OWN) and not has_permission(role, Permission.RETURN_READ):
        if row.customer_user_id != actor_id:
            raise AppError("Eligibility decision not found", code="not_found", status_code=404)
    return EligibilityDecisionPublic.from_model(row)


async def explain_eligibility_decision(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    decision_id: uuid.UUID,
    role: MemberRole,
) -> EligibilityDecisionPublic:
    if not (has_permission(role, Permission.RETURN_MANAGE) or has_permission(role, Permission.RETURN_READ)):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    repo = EligibilityDecisionRepository(session)
    row = await repo.get_in_store(store_id, decision_id)
    if row is None:
        raise AppError("Eligibility decision not found", code="not_found", status_code=404)
    snapshot = row.request_snapshot
    ai_text, ai_model = await build_ai_explanation(
        store_id=store_id,
        decision=row.decision,
        decision_code=row.decision_code,
        explanation=row.explanation,
        reason=str(snapshot.get("reason", "")),
        description=str(snapshot.get("description", "")),
        missing_information=row.missing_information,
        recommended_next_steps=row.recommended_next_steps,
        policy_citations=row.policy_references,
    )
    row.ai_explanation = ai_text
    row.ai_model = ai_model
    await session.commit()
    await session.refresh(row)
    return EligibilityDecisionPublic.from_model(row)


async def request_human_review(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    decision_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    ip_address: str | None,
) -> EligibilityDecisionPublic:
    if not (has_permission(role, Permission.RETURN_CREATE) or has_permission(role, Permission.RETURN_MANAGE)):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    repo = EligibilityDecisionRepository(session)
    row = await repo.get_in_store(store_id, decision_id)
    if row is None:
        raise AppError("Eligibility decision not found", code="not_found", status_code=404)
    if has_permission(role, Permission.RETURN_CREATE) and not has_permission(role, Permission.RETURN_MANAGE):
        if row.customer_user_id != actor_id:
            raise AppError("Eligibility decision not found", code="not_found", status_code=404)
    row.human_review_requested = True
    if row.decision == EligibilityDecision.ELIGIBLE:
        row.decision = EligibilityDecision.NEEDS_REVIEW
        row.explanation = f"{row.explanation} Customer requested human review."
    await record_audit(
        session,
        action="return.eligibility_review_requested",
        actor_user_id=actor_id,
        store_id=store_id,
        target_type="eligibility_decision",
        target_id=str(row.id),
        ip_address=ip_address,
        details={},
    )
    await session.commit()
    await session.refresh(row)
    return EligibilityDecisionPublic.from_model(row)


async def latest_for_return(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    return_id: uuid.UUID,
    role: MemberRole,
    actor_id: uuid.UUID,
) -> EligibilityDecisionPublic | None:
    return_req = await ReturnRepository(session).get_in_store(store_id, return_id)
    if return_req is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    if has_permission(role, Permission.RETURN_READ_OWN) and not has_permission(role, Permission.RETURN_READ):
        if return_req.customer_user_id != actor_id:
            raise AppError("Return not found", code="return_not_found", status_code=404)
    row = await EligibilityDecisionRepository(session).latest_for_return(store_id, return_id)
    return EligibilityDecisionPublic.from_model(row) if row else None