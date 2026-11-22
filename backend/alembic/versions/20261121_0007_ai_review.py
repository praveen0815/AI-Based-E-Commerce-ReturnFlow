"""AI return review LangGraph workflow persistence.

Revision ID: 0007_ai_review
Revises: 0006_eligibility
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_ai_review"
down_revision: Union[str, Sequence[str], None] = "0006_eligibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ai_review_run_status = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "AWAITING_HUMAN",
    "COMPLETED",
    "FAILED",
    "TIMED_OUT",
    name="ai_review_run_status",
    create_type=False,
)


def upgrade() -> None:
    ai_review_run_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "return_ai_review_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", ai_review_run_status, nullable=False),
        sa.Column("current_agent", sa.String(length=32), nullable=True),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("human_decision", sa.String(length=64), nullable=True),
        sa.Column("human_note", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["started_by_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_return_ai_review_runs_store_id", "return_ai_review_runs", ["store_id"])
    op.create_index("ix_return_ai_review_runs_return_id", "return_ai_review_runs", ["return_request_id"])

    op.create_table(
        "return_ai_review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("agent", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["return_ai_review_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_return_ai_review_events_run_id", "return_ai_review_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_return_ai_review_events_run_id", table_name="return_ai_review_events")
    op.drop_table("return_ai_review_events")
    op.drop_index("ix_return_ai_review_runs_return_id", table_name="return_ai_review_runs")
    op.drop_index("ix_return_ai_review_runs_store_id", table_name="return_ai_review_runs")
    op.drop_table("return_ai_review_runs")
    ai_review_run_status.drop(op.get_bind(), checkfirst=False)