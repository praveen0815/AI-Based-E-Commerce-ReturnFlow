"""Orders, line items, and return workflow tables.

Revision ID: 0003_commerce
Revises: 0002_auth
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_commerce"
down_revision: Union[str, Sequence[str], None] = "0002_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

order_status = postgresql.ENUM("PENDING", "PAID", "FULFILLED", "CANCELLED", name="order_status", create_type=False)
payment_status = postgresql.ENUM(
    "PENDING",
    "PAID",
    "PARTIALLY_REFUNDED",
    "REFUNDED",
    "FAILED",
    name="payment_status",
    create_type=False,
)
return_status = postgresql.ENUM(
    "REQUESTED",
    "UNDER_REVIEW",
    "APPROVED",
    "RETURN_IN_TRANSIT",
    "RECEIVED",
    "REFUND_PROCESSING",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
    "EXCHANGE_PROCESSING",
    name="return_status",
    create_type=False,
)
return_resolution = postgresql.ENUM(
    "REFUND",
    "EXCHANGE",
    "STORE_CREDIT",
    name="return_requested_resolution",
    create_type=False,
)


def upgrade() -> None:
    order_status.create(op.get_bind(), checkfirst=False)
    payment_status.create(op.get_bind(), checkfirst=False)
    return_status.create(op.get_bind(), checkfirst=False)
    return_resolution.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "sku", name="uq_products_store_sku"),
    )
    op.create_index("ix_products_store_id", "products", ["store_id"])

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fulfillment_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", order_status, nullable=False),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_sample", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("return_window_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "order_number", name="uq_orders_store_number"),
    )
    op.create_index("ix_orders_store_id", "orders", ["store_id"])
    op.create_index("ix_orders_customer_user_id", "orders", ["customer_user_id"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("line_name", sa.String(length=160), nullable=False),
        sa.Column("item_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "return_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_number", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requested_resolution", return_resolution, nullable=False),
        sa.Column("status", return_status, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_window_days", sa.Integer(), nullable=False),
        sa.Column("return_window_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "return_number", name="uq_returns_store_number"),
    )
    op.create_index("ix_return_requests_store_id", "return_requests", ["store_id"])
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])
    op.create_index("ix_return_requests_customer_user_id", "return_requests", ["customer_user_id"])

    op.create_table(
        "return_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_return_items_return_request_id", "return_items", ["return_request_id"])
    op.create_index("ix_return_items_order_item_id", "return_items", ["order_item_id"])

    op.create_table(
        "return_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", return_status, nullable=True),
        sa.Column("to_status", return_status, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_return_status_history_return_request_id", "return_status_history", ["return_request_id"])


def downgrade() -> None:
    op.drop_index("ix_return_status_history_return_request_id", table_name="return_status_history")
    op.drop_table("return_status_history")
    op.drop_index("ix_return_items_order_item_id", table_name="return_items")
    op.drop_index("ix_return_items_return_request_id", table_name="return_items")
    op.drop_table("return_items")
    op.drop_index("ix_return_requests_customer_user_id", table_name="return_requests")
    op.drop_index("ix_return_requests_order_id", table_name="return_requests")
    op.drop_index("ix_return_requests_store_id", table_name="return_requests")
    op.drop_table("return_requests")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer_user_id", table_name="orders")
    op.drop_index("ix_orders_store_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_products_store_id", table_name="products")
    op.drop_table("products")
    return_resolution.drop(op.get_bind(), checkfirst=False)
    return_status.drop(op.get_bind(), checkfirst=False)
    payment_status.drop(op.get_bind(), checkfirst=False)
    order_status.drop(op.get_bind(), checkfirst=False)