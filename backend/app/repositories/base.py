"""Repository base class for later persistence work.

Phase 1 has no domain repository. This class is the session boundary
later repositories should use.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Hold a request-scoped session. Subclasses add queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
