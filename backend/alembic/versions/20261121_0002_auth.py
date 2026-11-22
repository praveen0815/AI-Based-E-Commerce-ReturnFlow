"""Authentication, stores, memberships, and audit logs.

Revision ID: 0002_auth
Revises: 0001_baseline
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

member_role = postgresql.ENUM(
    "OWNER",
    "ADMIN",
    "MANAGER",
    "SUPPORT_AGENT",
    "CUSTOMER",
    name="store_member_role",
    create_type=False,
)


def upgrade() -> None:
    member_role.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_stores_slug"),
    )
    op.create_table(
        "store_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", member_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id", "user_id", name="uq_store_memberships_store_user"),
    )
    op.create_index("ix_store_memberships_user_id", "store_memberships", ["user_id"])
    op.create_index("ix_store_memberships_store_id", "store_memberships", ["store_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_store_created", "audit_logs", ["store_id", "created_at"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_store_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_store_memberships_store_id", table_name="store_memberships")
    op.drop_index("ix_store_memberships_user_id", table_name="store_memberships")
    op.drop_table("store_memberships")
    op.drop_table("stores")
    op.drop_table("users")
    member_role.drop(op.get_bind(), checkfirst=False)
