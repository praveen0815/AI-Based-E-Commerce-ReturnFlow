"""Versioned store return policy rule configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.core.order_enums import OrderStatus
from app.core.return_lifecycle import RequestedResolution


class StorePolicyRulesConfig(BaseModel):
    """Serializable rules evaluated in Python only."""

    return_window_days_default: int = Field(default=30, ge=1, le=365)
    allowed_order_statuses: list[OrderStatus] = Field(
        default_factory=lambda: [OrderStatus.FULFILLED],
    )
    allowed_resolutions: list[RequestedResolution] = Field(
        default_factory=lambda: [
            RequestedResolution.REFUND,
            RequestedResolution.EXCHANGE,
            RequestedResolution.STORE_CREDIT,
        ],
    )
    block_final_sale: bool = True
    require_item_condition: bool = False
    allowed_item_conditions: list[str] = Field(default_factory=lambda: ["NEW", "OPENED", "USED", "DAMAGED"])
    damaged_requires_review: bool = True
    min_reason_length: int = Field(default=2, ge=1, le=80)
    min_description_length: int = Field(default=2, ge=1, le=500)
    require_paid_for_refund: bool = True

    @model_validator(mode="after")
    def normalize_conditions(self) -> "StorePolicyRulesConfig":
        normalized = {value.strip().upper() for value in self.allowed_item_conditions if value.strip()}
        self.allowed_item_conditions = sorted(normalized)
        return self