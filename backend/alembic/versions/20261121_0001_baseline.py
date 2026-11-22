"""Baseline migration.

Phase 1 establishes the Alembic revision chain before domain tables exist.
Applying this revision creates Alembic's version table and nothing else.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-21
"""

from typing import Sequence, Union

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
