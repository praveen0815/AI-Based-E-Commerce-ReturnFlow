# Phase 5 report — RAG policy assistant

## Scope delivered

- Text cleaning and LangChain recursive chunking with overlap and page hints
- Sentence Transformers embeddings (mock provider in tests)
- ChromaDB per-store collections with cosine search and metadata
- Index, reindex, and delete-index APIs with document-level tracking
- Semantic search and grounded Q&A with citations and relevance threshold
- Mock LLM by default; Gemini via `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`
- Policy chat UI with session history, citations, feedback, and reindex control

## Verification

```powershell
cd backend
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_rag.py -q
```

Optional live Gemini smoke (never logs secrets):

```powershell
$env:GEMINI_API_KEY = "<your-key>"
.\.venv\Scripts\python -m pytest tests/test_rag_live.py -m live_llm -q
```