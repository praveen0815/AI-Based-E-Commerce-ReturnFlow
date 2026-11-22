"""Return status machine rules."""

from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.core.return_lifecycle import ReturnStatus, assert_transition, can_customer_cancel


def test_happy_path_transitions() -> None:
    assert_transition(ReturnStatus.REQUESTED, ReturnStatus.UNDER_REVIEW)
    assert_transition(ReturnStatus.UNDER_REVIEW, ReturnStatus.APPROVED)
    assert_transition(ReturnStatus.APPROVED, ReturnStatus.RETURN_IN_TRANSIT)
    assert_transition(ReturnStatus.RETURN_IN_TRANSIT, ReturnStatus.RECEIVED)
    assert_transition(ReturnStatus.RECEIVED, ReturnStatus.REFUND_PROCESSING)
    assert_transition(ReturnStatus.REFUND_PROCESSING, ReturnStatus.COMPLETED)


def test_invalid_transition_raises() -> None:
    with pytest.raises(AppError) as caught:
        assert_transition(ReturnStatus.REQUESTED, ReturnStatus.COMPLETED)
    assert caught.value.code == "invalid_return_transition"


def test_customer_cancel_window() -> None:
    assert can_customer_cancel(ReturnStatus.REQUESTED)
    assert can_customer_cancel(ReturnStatus.UNDER_REVIEW)
    assert not can_customer_cancel(ReturnStatus.APPROVED)