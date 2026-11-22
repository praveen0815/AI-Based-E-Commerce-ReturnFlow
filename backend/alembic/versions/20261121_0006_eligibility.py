"""Return eligibility decisions and versioned policy rules.

Revision ID: 0006_eligibility
Revises: 0005_rag
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_eligibility"
down_revision: Union[str, Sequence[str], None] = "0005_rag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

eligibility_decision = postgresql.ENUM(
    "ELIGIBLE",
    "INELIGIBLE",
    "NEEDS_REVIEW",
    name="eligibility_decision",
    create_type=False,
)


def upgrade() -> None:
    eligibility_decision.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "store_return_policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("store_id", "version", name="uq_store_policy_rules_version"),
    )
    op.create_index("ix_store_return_policy_rules_store_id", "store_return_policy_rules", ["store_id"])

    op.create_table(
        "return_eligibility_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", eligibility_decision, nullable=False),
        sa.Column("decision_code", sa.String(length=64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("decision_reason", sa.String(length=64), nullable=False),
        sa.Column("policy_rule_version", sa.Integer(), nullable=False),
        sa.Column("policy_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_information", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_next_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column("human_review_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_return_eligibility_decisions_store_id", "return_eligibility_decisions", ["store_id"])
    op.create_index("ix_return_eligibility_decisions_order_id", "return_eligibility_decisions", ["order_id"])
    op.create_index(
        "ix_return_eligibility_decisions_return_request_id",
        "return_eligibility_decisions",
        ["return_request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_return_eligibility_decisions_return_request_id", table_name="return_eligibility_decisions")
    op.drop_index("ix_return_eligibility_decisions_order_id", table_name="return_eligibility_decisions")
    op.drop_index("ix_return_eligibility_decisions_store_id", table_name="return_eligibility_decisions")
    op.drop_table("return_eligibility_decisions")
    op.drop_index("ix_store_return_policy_rules_store_id", table_name="store_return_policy_rules")
    op.drop_table("store_return_policy_rules")
    eligibility_decision.drop(op.get_bind(), checkfirst=False)