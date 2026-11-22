"""SQLAlchemy declarative base shared by models and Alembic."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models. Phase 1 registers no domain tables."""
