"""Store knowledge documents.

Revision ID: 0004_knowledge
Revises: 0003_commerce
Create Date: 2026-11-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_knowledge"
down_revision: Union[str, Sequence[str], None] = "0003_commerce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

knowledge_document_type = postgresql.ENUM(
    "RETURN_POLICY",
    "REFUND_POLICY",
    "SHIPPING_POLICY",
    "WARRANTY",
    "PRODUCT_CONDITIONS",
    "STORE_SOP",
    "CUSTOM",
    name="knowledge_document_type",
    create_type=False,
)
knowledge_processing_status = postgresql.ENUM(
    "UPLOADED",
    "PROCESSING",
    "PROCESSED",
    "FAILED",
    name="knowledge_processing_status",
    create_type=False,
)


def upgrade() -> None:
    knowledge_document_type.create(op.get_bind(), checkfirst=False)
    knowledge_processing_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "store_knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("document_type", knowledge_document_type, nullable=False),
        sa.Column("processing_status", knowledge_processing_status, nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_store_knowledge_documents_store_id", "store_knowledge_documents", ["store_id"])
    op.create_index(
        "ix_store_knowledge_documents_store_status",
        "store_knowledge_documents",
        ["store_id", "processing_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_store_knowledge_documents_store_status", table_name="store_knowledge_documents")
    op.drop_index("ix_store_knowledge_documents_store_id", table_name="store_knowledge_documents")
    op.drop_table("store_knowledge_documents")
    knowledge_processing_status.drop(op.get_bind(), checkfirst=False)
    knowledge_document_type.drop(op.get_bind(), checkfirst=False)