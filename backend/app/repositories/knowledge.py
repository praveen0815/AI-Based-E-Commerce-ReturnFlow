"""Store knowledge document queries."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select

from app.core.knowledge_enums import KnowledgeDocumentType, KnowledgeProcessingStatus
from app.models.knowledge_document import StoreKnowledgeDocument
from app.repositories.base import BaseRepository

_SORT_COLUMNS = {
    "uploaded_at": StoreKnowledgeDocument.uploaded_at,
    "original_filename": StoreKnowledgeDocument.original_filename,
    "document_type": StoreKnowledgeDocument.document_type,
    "processing_status": StoreKnowledgeDocument.processing_status,
}


class KnowledgeDocumentRepository(BaseRepository):
    def add(self, document: StoreKnowledgeDocument) -> None:
        self.session.add(document)

    async def get_in_store(self, store_id: uuid.UUID, document_id: uuid.UUID) -> StoreKnowledgeDocument | None:
        stmt = select(StoreKnowledgeDocument).where(
            StoreKnowledgeDocument.id == document_id,
            StoreKnowledgeDocument.store_id == store_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_store(
        self,
        store_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        sort: str,
        direction: str,
        document_type: KnowledgeDocumentType | None,
        processing_status: KnowledgeProcessingStatus | None,
        q: str | None,
    ) -> tuple[list[StoreKnowledgeDocument], int]:
        base: Select[tuple[StoreKnowledgeDocument]] = select(StoreKnowledgeDocument).where(
            StoreKnowledgeDocument.store_id == store_id
        )
        if document_type is not None:
            base = base.where(StoreKnowledgeDocument.document_type == document_type)
        if processing_status is not None:
            base = base.where(StoreKnowledgeDocument.processing_status == processing_status)
        if q:
            term = f"%{q.strip().lower()}%"
            base = base.where(
                or_(
                    func.lower(StoreKnowledgeDocument.original_filename).like(term),
                    func.lower(StoreKnowledgeDocument.extracted_text).like(term),
                )
            )
        sort_col = _SORT_COLUMNS.get(sort, StoreKnowledgeDocument.uploaded_at)
        order = sort_col.desc() if direction == "desc" else sort_col.asc()
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = base.order_by(order).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total