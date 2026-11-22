# Phase 11 — Deployment & GitHub release preparation

**Version:** 0.11.0  
**Date:** 2026-11-21

## Objective outcome

ReturnFlow is packaged for **reproducible local deployment** and **public GitHub presentation**: Docker images, full Compose profile, nginx API proxy, persistent volumes, migration on API startup, updated env templates, and release documentation.

---

## Architecture

```text
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │ HTTP :8080
                    ┌──────▼──────┐
                    │ nginx (web) │── SPA static files
                    └──────┬──────┘
                           │ /api/*
                    ┌──────▼──────┐
                    │  FastAPI    │── Alembic on entrypoint
                    └─┬────┬────┬┘
          ┌───────────┘    │    └───────────┐
    ┌─────▼─────┐    ┌─────▼─────┐    ┌──────▼──────┐
    │ PostgreSQL│    │   Redis   │    │ Volumes:    │
    │  (data)   │    │ (sessions)│    │ knowledge + │
    └───────────┘    └───────────┘    │ chroma      │
                                        └─────────────┘
```

---

## Feature list (Phases 1–10)

| Area | Capability |
| --- | --- |
| Auth | Register, login, JWT + Redis session allowlist, Argon2 |
| Tenancy | Stores, roles, `X-Store-ID`, membership RBAC |
| Commerce | Orders, returns, validated lifecycle |
| Knowledge | Upload PDF/DOCX/TXT/MD, extraction |
| RAG | Chroma per store, semantic search, policy chat |
| Eligibility | Deterministic rules + optional AI explain |
| AI review | LangGraph agents, human checkpoint |
| Fulfillment | Mock label + refund, idempotency |
| Analytics | Admin + customer dashboards |
| Ops UI | Queue filters, return detail workflows |

---

## Tech stack

| Layer | Stack |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind, Axios |
| API | FastAPI, Pydantic, SQLAlchemy 2 async, Alembic |
| Data | PostgreSQL 16, Redis 7 |
| AI (optional) | Chroma, mock/sentence-transformers, mock/Gemini LLM, LangGraph |
| Deploy | Docker, nginx, Compose profiles |

---

## Docker verification

| Check | Status in audit environment |
| --- | --- |
| `backend/Dockerfile` + entrypoint migrations | **Implemented** |
| `frontend/Dockerfile` + `nginx.conf` API proxy | **Implemented** |
| `docker-compose.yml` postgres/redis volumes + health | **Implemented** |
| Full profile `api` + `web` + knowledge/chroma volumes | **Implemented** |
| `docker compose build` / full stack boot | **Not run** — Docker daemon unavailable on audit host |
| Manual smoke (register → analytics) | **Pending** — run locally after `docker compose --profile full up` |

Details: [docs/DEPLOYMENT.md](DEPLOYMENT.md).

---

## Test results

| Suite | Notes |
| --- | --- |
| Backend `pytest` | Requires Postgres on `returnflow_test` + Redis DB 15; see [PHASE10_REPORT.md](PHASE10_REPORT.md) |
| Default pytest | Excludes `live_llm`; mock providers via `conftest` |
| `npm run build` | **Pass** (frontend TypeScript + Vite) |
| Integration marker | `RUN_INTEGRATION=1 pytest -m integration` |

**Mock-labelled tests:** RAG, AI review, eligibility explain, fulfillment refunds/labels.

**Live LLM:** Only when `GEMINI_API_KEY` set and `pytest -m live_llm` — not claimed for default release.

---

## Security audit (summary)

Re-use [PHASE10_REPORT.md](PHASE10_REPORT.md). Phase 11 additions:

- CORS includes Docker web origin in `.env.example`
- nginx security headers; 12 MB upload limit for knowledge proxy path
- Secrets remain in `.env` only; `.gitignore` covers `data/`, keys, env variants
- Production blocks placeholder JWT and `DEBUG=true` when `APP_ENV=production`

---

## Known limitations

- Mock payment and shipping; notification rows only  
- Default Docker-oriented `.env.example` uses `LLM_PROVIDER=mock` and `RAG_EMBEDDINGS_PROVIDER=mock`  
- No frontend automated E2E  
- First API container start may be slow (migrations + optional embedding model load if not mock)  
- Concurrent fulfillment idempotency race (documented in Phase 10)

---

## GitHub release checklist

See [GITHUB_RELEASE_CHECKLIST.md](GITHUB_RELEASE_CHECKLIST.md). **Commits and push are manual** — this phase does not push to remote.

### Git status guidance

Before release, verify:

```powershell
git status
git check-ignore -v .env
git ls-files data frontend/dist
```

Remove any accidental secrets or generated uploads from the index before commit.

---

## Screenshots

Place validated UI captures in `docs/screenshots/` after completing the manual smoke list in [DEPLOYMENT.md](DEPLOYMENT.md). Do not ship placeholder images as if they were tested.

Phase 12+ not started.