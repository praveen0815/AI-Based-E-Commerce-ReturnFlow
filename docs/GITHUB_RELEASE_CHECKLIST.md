# GitHub release checklist

Use this before tagging **v0.11.0** (or later). **Do not push secrets or generated data.**

## Repository hygiene

- [ ] `.env` not tracked (`git check-ignore .env`)
- [ ] No `data/knowledge/`, `data/chroma/`, or `backend/tests/.chroma_pytest/` in git
- [ ] No API keys in history (`git grep -i gemini_api` on tracked files)
- [ ] `frontend/dist/` and `node_modules/` ignored
- [ ] `backend/.venv/` ignored

## Verification commands

```powershell
docker compose up -d postgres redis
cd backend
.\.venv\Scripts\alembic upgrade head
$env:DATABASE_URL = "postgresql+asyncpg://returnflow:<password>@localhost:5432/returnflow_test"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/ -q

cd ..\frontend
npm run build

docker compose --profile full build
docker compose --profile full up -d
curl http://localhost:8080/api/v1/health
curl http://localhost:8000/api/v1/ready
```

## Release artifacts

- [ ] Update `README.md` and `docs/PHASE11_REPORT.md`
- [ ] Tag: `v0.11.0` with notes from Phase 11 report
- [ ] Screenshots: capture **after** manual UI smoke test; store under `docs/screenshots/` (optional)
- [ ] Do **not** claim live Gemini/refunds/shipping unless you ran them with real keys/providers

## Suggested commit groups (do not auto-push)

1. Docker / compose / nginx / entrypoint  
2. Frontend API base URL + env examples  
3. Documentation + version bump 0.11.0  

## Public demo disclosure

State clearly in the release notes:

- Mock LLM and mock embeddings by default  
- Mock refund and shipping labels  
- LangGraph AI review with human checkpoint — recommendations are not auto-approval  