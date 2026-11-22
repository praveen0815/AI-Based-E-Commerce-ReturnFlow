"""Deterministic return eligibility — no LLM involvement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.eligibility_enums import (
    EligibilityConfidence,
    EligibilityDecision,
    EligibilityDecisionCode,
)
from app.core.order_enums import OrderStatus, PaymentStatus
from app.core.return_lifecycle import RequestedResolution
from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.policy_rules import StorePolicyRulesConfig
from app.services.orders import return_window_ends


@dataclass
class EligibilityItemInput:
    order_item_id: uuid.UUID
    quantity: int
    condition: str | None = None


@dataclass
class EligibilityEvaluateInput:
    order_id: uuid.UUID
    customer_user_id: uuid.UUID
    reason: str
    description: str
    requested_resolution: RequestedResolution
    items: list[EligibilityItemInput]


@dataclass
class EligibilityRuleOutcome:
    decision: EligibilityDecision
    code: EligibilityDecisionCode
    explanation: str
    confidence: EligibilityConfidence
    policy_references: list[dict[str, Any]] = field(default_factory=list)
    missing_information: list[dict[str, str]] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)


def evaluate_eligibility(
    *,
    order: Order | None,
    order_items: dict[uuid.UUID, OrderItem],
    returned_qty: dict[uuid.UUID, int],
    policy: StorePolicyRulesConfig,
    policy_version: int,
    payload: EligibilityEvaluateInput,
    actor_is_customer: bool,
) -> EligibilityRuleOutcome:
    refs = [_policy_ref(policy_version, "store_return_policy_rules")]

    if order is None:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_ORDER_NOT_FOUND,
            explanation="The order was not found in this store.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs,
            recommended_next_steps=["Confirm the order number and store selection."],
        )

    if actor_is_customer and order.customer_user_id != payload.customer_user_id:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_ORDER_NOT_OWNED,
            explanation="You can only evaluate returns for your own orders.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs,
        )

    if order.status not in policy.allowed_order_statuses:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_ORDER_STATUS,
            explanation=f"Orders in status {order.status.value} cannot be returned under policy v{policy_version}.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs + [_policy_ref(policy_version, "allowed_order_statuses", str(order.status.value))],
        )

    if order.fulfillment_date is None:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.NEEDS_REVIEW,
            code=EligibilityDecisionCode.NEEDS_REVIEW_MISSING_FULFILLMENT,
            explanation="Delivery or fulfillment date is missing; return window cannot be calculated.",
            confidence=EligibilityConfidence.MEDIUM,
            policy_references=refs,
            missing_information=[{"field": "fulfillment_date", "label": "Delivery date"}],
            recommended_next_steps=["Ask a team member to confirm delivery before approving a return."],
        )

    window_end = return_window_ends(order)
    if window_end is None or datetime.now(UTC) > window_end:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_RETURN_WINDOW_EXPIRED,
            explanation=f"The return window ended on {window_end.isoformat() if window_end else 'unknown'}.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs + [_policy_ref(policy_version, "return_window_days", str(order.return_window_days))],
        )

    if (
        payload.requested_resolution == RequestedResolution.REFUND
        and policy.require_paid_for_refund
        and order.payment_status not in {PaymentStatus.PAID, PaymentStatus.PARTIALLY_REFUNDED}
    ):
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_PAYMENT_STATUS,
            explanation=f"Refunds require a paid order; payment status is {order.payment_status.value}.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs + [_policy_ref(policy_version, "require_paid_for_refund", "true")],
        )

    if payload.requested_resolution not in policy.allowed_resolutions:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.INELIGIBLE,
            code=EligibilityDecisionCode.INELIGIBLE_RESOLUTION_NOT_ALLOWED,
            explanation=f"{payload.requested_resolution.value} is not allowed under current store policy.",
            confidence=EligibilityConfidence.HIGH,
            policy_references=refs + [_policy_ref(policy_version, "allowed_resolutions")],
        )

    if len(payload.reason.strip()) < policy.min_reason_length:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.NEEDS_REVIEW,
            code=EligibilityDecisionCode.NEEDS_REVIEW_INSUFFICIENT_DETAIL,
            explanation="Return reason is too short for an automatic decision.",
            confidence=EligibilityConfidence.MEDIUM,
            policy_references=refs,
            missing_information=[{"field": "reason", "label": "Return reason"}],
            recommended_next_steps=["Provide a clearer return reason."],
        )

    if len(payload.description.strip()) < policy.min_description_length:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.NEEDS_REVIEW,
            code=EligibilityDecisionCode.NEEDS_REVIEW_INSUFFICIENT_DETAIL,
            explanation="Return description is too short for an automatic decision.",
            confidence=EligibilityConfidence.MEDIUM,
            policy_references=refs,
            missing_information=[{"field": "description", "label": "Return description"}],
            recommended_next_steps=["Add detail about item condition and why you are returning it."],
        )

    if not payload.items:
        return EligibilityRuleOutcome(
            decision=EligibilityDecision.NEEDS_REVIEW,
            code=EligibilityDecisionCode.NEEDS_REVIEW_UNKNOWN_ITEM,
            explanation="No line items were selected for this evaluation.",
            confidence=EligibilityConfidence.MEDIUM,
            policy_references=refs,
            missing_information=[{"field": "items", "label": "Items to return"}],
        )

    for line in payload.items:
        order_line = order_items.get(line.order_item_id)
        if order_line is None:
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.NEEDS_REVIEW,
                code=EligibilityDecisionCode.NEEDS_REVIEW_UNKNOWN_ITEM,
                explanation="A line item does not belong to this order.",
                confidence=EligibilityConfidence.MEDIUM,
                policy_references=refs,
                recommended_next_steps=["Refresh the order and select valid line items."],
            )

        meta = order_line.item_metadata or {}
        if policy.block_final_sale and bool(meta.get("final_sale")):
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.INELIGIBLE,
                code=EligibilityDecisionCode.INELIGIBLE_FINAL_SALE,
                explanation=f"{order_line.line_name} is marked final sale and cannot be returned.",
                confidence=EligibilityConfidence.HIGH,
                policy_references=refs + [_policy_ref(policy_version, "block_final_sale", order_line.sku)],
            )

        if meta.get("returnable") is False:
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.INELIGIBLE,
                code=EligibilityDecisionCode.INELIGIBLE_ITEM_NOT_RETURNABLE,
                explanation=f"{order_line.line_name} is not returnable per catalog rules.",
                confidence=EligibilityConfidence.HIGH,
                policy_references=refs + [_policy_ref(policy_version, "item_returnable", order_line.sku)],
            )

        already = returned_qty.get(order_line.id, 0)
        available = order_line.quantity - already
        if line.quantity > available:
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.INELIGIBLE,
                code=EligibilityDecisionCode.INELIGIBLE_QUANTITY_EXCEEDED,
                explanation=f"Requested quantity {line.quantity} exceeds {available} returnable for {order_line.line_name}.",
                confidence=EligibilityConfidence.HIGH,
                policy_references=refs + [_policy_ref(policy_version, "return_quantity", order_line.sku)],
            )

        condition = (line.condition or "").strip().upper()
        if policy.require_item_condition and not condition:
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.NEEDS_REVIEW,
                code=EligibilityDecisionCode.NEEDS_REVIEW_MISSING_CONDITION,
                explanation=f"Product condition is required for {order_line.line_name}.",
                confidence=EligibilityConfidence.MEDIUM,
                policy_references=refs + [_policy_ref(policy_version, "require_item_condition")],
                missing_information=[{"field": "condition", "label": f"Condition for {order_line.line_name}"}],
                recommended_next_steps=["Indicate whether the item is new, opened, used, or damaged."],
            )

        if condition and condition not in policy.allowed_item_conditions:
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.NEEDS_REVIEW,
                code=EligibilityDecisionCode.NEEDS_REVIEW_POLICY_CONFLICT,
                explanation=f"Condition '{condition}' is not listed in store policy.",
                confidence=EligibilityConfidence.MEDIUM,
                policy_references=refs + [_policy_ref(policy_version, "allowed_item_conditions")],
                recommended_next_steps=["Request human review or update the condition label."],
            )

        if policy.damaged_requires_review and condition == "DAMAGED":
            return EligibilityRuleOutcome(
                decision=EligibilityDecision.NEEDS_REVIEW,
                code=EligibilityDecisionCode.NEEDS_REVIEW_DAMAGED_ITEM,
                explanation="Damaged items require staff review before approval.",
                confidence=EligibilityConfidence.MEDIUM,
                policy_references=refs + [_policy_ref(policy_version, "damaged_requires_review", order_line.sku)],
                recommended_next_steps=["Route to a manager for inspection or photos."],
            )

    return EligibilityRuleOutcome(
        decision=EligibilityDecision.ELIGIBLE,
        code=EligibilityDecisionCode.ELIGIBLE_ALL_RULES_PASSED,
        explanation="All configured business rules passed for this return request.",
        confidence=EligibilityConfidence.HIGH,
        policy_references=refs,
        recommended_next_steps=["Submit the return request or advance to fulfillment."],
    )


def _policy_ref(version: int, rule_key: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "source": "store_return_policy_rules",
        "version": version,
        "rule_key": rule_key,
        "detail": detail,
    }