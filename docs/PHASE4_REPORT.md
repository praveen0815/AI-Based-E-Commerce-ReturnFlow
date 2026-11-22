# Phase 4 report — knowledge base

## Scope delivered

- Store-scoped knowledge documents with upload, listing, detail, delete, and reprocess APIs
- Processing lifecycle: `UPLOADED` → `PROCESSING` → `PROCESSED` with `FAILED` on extraction errors
- Supported formats: PDF, DOCX, TXT, Markdown
- Content and extension validation, size limits, and filesystem storage under `data/knowledge/`
- Permissions: `knowledge:read` (staff) and `knowledge:manage` (owner, admin, manager)
- React knowledge center with drag-and-drop upload, filters, status indicators, preview, and delete confirmation

## Out of scope

- Embeddings, vector indexes, and RAG retrieval

## Verification

```powershell
cd backend
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_knowledge.py
```