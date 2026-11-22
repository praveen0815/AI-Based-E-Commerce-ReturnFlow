"""Return logistics, refunds, notifications, idempotency.

Revision ID: 0008_fulfillment
Revises: 0007_ai_review
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_fulfillment"
down_revision: Union[str, Sequence[str], None] = "0007_ai_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

refund_provider_status = postgresql.ENUM(
    "ELIGIBLE",
    "INELIGIBLE",
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="refund_provider_status",
    create_type=False,
)
shipment_provider_status = postgresql.ENUM(
    "LABEL_PENDING",
    "LABEL_READY",
    "IN_TRANSIT",
    "DELIVERED",
    "FAILED",
    name="shipment_provider_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE return_status ADD VALUE IF NOT EXISTS 'LABEL_PENDING'")
    op.execute("ALTER TYPE return_status ADD VALUE IF NOT EXISTS 'LABEL_GENERATED'")
    op.execute("ALTER TYPE return_status ADD VALUE IF NOT EXISTS 'REFUND_PENDING'")
    op.execute("ALTER TYPE return_status ADD VALUE IF NOT EXISTS 'REFUND_COMPLETED'")

    refund_provider_status.create(op.get_bind(), checkfirst=False)
    shipment_provider_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "return_shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", shipment_provider_status, nullable=False),
        sa.Column("carrier", sa.String(length=64), nullable=False),
        sa.Column("tracking_number", sa.String(length=64), nullable=True),
        sa.Column("label_url", sa.String(length=512), nullable=True),
        sa.Column("provider_ref", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "idempotency_key", name="uq_return_shipments_idempotency"),
    )
    op.create_index("ix_return_shipments_return_id", "return_shipments", ["return_request_id"])

    op.create_table(
        "return_refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", refund_provider_status, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider_ref", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "idempotency_key", name="uq_return_refunds_idempotency"),
    )
    op.create_index("ix_return_refunds_return_id", "return_refunds", ["return_request_id"])

    op.create_table(
        "return_notification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_preview", sa.String(length=500), nullable=False),
        sa.Column("mock_delivered", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_return_notification_events_return_id", "return_notification_events", ["return_request_id"])

    op.create_table(
        "fulfillment_idempotency",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "idempotency_key", name="uq_fulfillment_idempotency"),
    )


def downgrade() -> None:
    op.drop_table("fulfillment_idempotency")
    op.drop_index("ix_return_notification_events_return_id", table_name="return_notification_events")
    op.drop_table("return_notification_events")
    op.drop_index("ix_return_refunds_return_id", table_name="return_refunds")
    op.drop_table("return_refunds")
    op.drop_index("ix_return_shipments_return_id", table_name="return_shipments")
    op.drop_table("return_shipments")
    shipment_provider_status.drop(op.get_bind(), checkfirst=False)
    refund_provider_status.drop(op.get_bind(), checkfirst=False)