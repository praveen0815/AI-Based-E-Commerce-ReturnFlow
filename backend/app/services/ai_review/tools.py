"""Tenant-scoped tools for AI review agents — no SQL, shell, or open network."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.return_lifecycle import RequestedResolution
from app.repositories.orders import OrderRepository
from app.repositories.returns import ReturnRepository
from app.services.eligibility.engine import EligibilityEvaluateInput, EligibilityItemInput, evaluate_eligibility
from app.services.eligibility.policy_rules_service import get_active_policy_rules
from app.services.rag.retrieval import hits_to_citations, search_knowledge


@dataclass(frozen=True)
class ReturnContext:
    store_id: uuid.UUID
    return_id: uuid.UUID
    return_number: str
    order_id: uuid.UUID
    order_number: str
    reason: str
    description: str
    requested_resolution: RequestedResolution
    items: list[dict]
    status: str


async def load_return_context(session: AsyncSession, *, store_id: uuid.UUID, return_id: uuid.UUID) -> ReturnContext:
    found = await ReturnRepository(session).get_in_store(store_id, return_id)
    if found is None:
        raise AppError("Return not found", code="return_not_found", status_code=404)
    return ReturnContext(
        store_id=store_id,
        return_id=return_id,
        return_number=found.return_number,
        order_id=found.order_id,
        order_number=found.order.order_number,
        reason=found.reason,
        description=found.description,
        requested_resolution=found.requested_resolution,
        items=[
            {
                "order_item_id": str(line.order_item_id),
                "line_name": line.order_item.line_name if line.order_item else "",
                "quantity": line.quantity,
            }
            for line in found.items
        ],
        status=found.status.value,
    )


async def tool_search_policies(store_id: uuid.UUID, query: str) -> list[dict]:
    hits = await search_knowledge(store_id, query=query, top_k=5)
    return hits_to_citations(hits)


async def tool_evaluate_eligibility(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    context: ReturnContext,
) -> dict:
    policy, policy_version, _ = await get_active_policy_rules(session, store_id)
    order = await OrderRepository(session).get_in_store(store_id, context.order_id)
    order_items = {line.id: line for line in order.items} if order else {}
    returned_qty: dict[uuid.UUID, int] = {}
    if order:
        for line in order.items:
            returned_qty[line.id] = await ReturnRepository(session).returned_quantity(line.id)
    found = await ReturnRepository(session).get_in_store(store_id, context.return_id)
    payload = EligibilityEvaluateInput(
        order_id=context.order_id,
        customer_user_id=found.customer_user_id if found else uuid.uuid4(),
        reason=context.reason,
        description=context.description,
        requested_resolution=context.requested_resolution,
        items=[
            EligibilityItemInput(
                order_item_id=uuid.UUID(item["order_item_id"]),
                quantity=int(item["quantity"]),
                condition=None,
            )
            for item in context.items
        ],
    )
    outcome = evaluate_eligibility(
        order=order,
        order_items=order_items,
        returned_qty=returned_qty,
        policy=policy,
        policy_version=policy_version,
        payload=payload,
        actor_is_customer=False,
    )
    return {
        "decision": outcome.decision.value,
        "decision_code": outcome.code.value,
        "explanation": outcome.explanation,
        "policy_references": outcome.policy_references,
        "missing_information": outcome.missing_information,
        "recommended_next_steps": outcome.recommended_next_steps,
        "policy_rule_version": policy_version,
        "locked": True,
    }