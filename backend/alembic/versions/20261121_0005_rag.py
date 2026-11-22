"""RAG index fields and policy chat feedback.

Revision ID: 0005_rag
Revises: 0004_knowledge
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_rag"
down_revision: Union[str, Sequence[str], None] = "0004_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

knowledge_index_status = postgresql.ENUM(
    "NOT_INDEXED",
    "INDEXING",
    "INDEXED",
    "INDEX_FAILED",
    name="knowledge_index_status",
    create_type=False,
)


def upgrade() -> None:
    knowledge_index_status.create(op.get_bind(), checkfirst=False)

    op.add_column(
        "store_knowledge_documents",
        sa.Column(
            "index_status",
            knowledge_index_status,
            nullable=False,
            server_default="NOT_INDEXED",
        ),
    )
    op.add_column("store_knowledge_documents", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("store_knowledge_documents", sa.Column("indexed_chunk_count", sa.Integer(), nullable=True))
    op.add_column("store_knowledge_documents", sa.Column("index_error", sa.String(length=500), nullable=True))

    op.create_table(
        "policy_chat_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer_excerpt", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_policy_chat_feedback_store_id", "policy_chat_feedback", ["store_id"])


def downgrade() -> None:
    op.drop_index("ix_policy_chat_feedback_store_id", table_name="policy_chat_feedback")
    op.drop_table("policy_chat_feedback")
    op.drop_column("store_knowledge_documents", "index_error")
    op.drop_column("store_knowledge_documents", "indexed_chunk_count")
    op.drop_column("store_knowledge_documents", "indexed_at")
    op.drop_column("store_knowledge_documents", "index_status")
    knowledge_index_status.drop(op.get_bind(), checkfirst=False)