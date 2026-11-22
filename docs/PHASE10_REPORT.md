# Phase 10 — Integration & security audit (Phases 1–9)

**Release version:** 0.10.0  
**Audit date:** 2026-11-21  
**Scope:** Backend, security, test matrix, frontend readiness. No Phase 11 work.

---

## Executive summary

ReturnFlow Phases 1–9 form a **coherent multi-tenant returns platform**: JWT + Redis sessions, store-scoped RBAC, validated return lifecycle, deterministic eligibility, mock RAG/LLM (testable), LangGraph review with human checkpoint, mock refund/logistics with idempotency, and analytics-backed dashboards.

**Fixes in this phase**

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| P10-001 | Medium | Browser CORS preflight did not allow `Idempotency-Key` | Added header to `CORSMiddleware` in `app/main.py` |
| P10-002 | Low | Pytest could run optional live Gemini test unintentionally | `addopts = "-m 'not live_llm'"` in `pyproject.toml` |
| P10-003 | Low | Version drift | API `__version__` / package set to **0.10.0** |

**Release blockers (operational, not code defects)**

1. PostgreSQL + Redis must be running; `returnflow` and `returnflow_test` migrated to `0008_fulfillment` head.
2. Production requires strong `JWT_SECRET`, non-placeholder `DATABASE_URL`, explicit `CORS_ORIGINS`.
3. No automated frontend unit/E2E suite (manual `npm run build` only).

---

## Test report

### How to run

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic upgrade head
$env:DATABASE_URL = "postgresql+asyncpg://returnflow:returnflow_local_dev@localhost:5432/returnflow_test"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/ -q
cd ..\frontend
npm run build
```

Optional:

```powershell
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python -m pytest -m integration -q
.\.venv\Scripts\python -m pytest -m live_llm -q   # needs GEMINI_API_KEY
```

### Suites (all use **mock** LLM/RAG unless noted)

| Module | Focus |
|--------|--------|
| `test_auth.py`, `test_tokens.py` | Register, login, logout, JWT + Redis allowlist |
| `test_permissions.py` | Role → permission mapping |
| `test_tenant_isolation.py` | Cross-store header/membership denial |
| `test_commerce.py` | Orders, returns, sample data |
| `test_return_lifecycle.py` | Status transition rules |
| `test_knowledge.py` | Upload, extraction, tenant isolation |
| `test_rag.py` | Chroma mock embeddings, grounded ask (`mock_llm` via env) |
| `test_eligibility.py` | Deterministic engine + store rules |
| `test_ai_review.py` | LangGraph mock structured LLM, human resume |
| `test_fulfillment.py` | Idempotency, mock refund/label, permissions |
| `test_analytics.py` | KPI queries, admin vs customer auth |
| `test_phase10_security.py` | CORS, traversal filename, fail-closed routes |
| `test_integration_matrix.py` | Suite manifest + mock provider env check |
| `test_config.py`, `test_errors.py`, `test_health.py`, `test_logging.py` | Foundation |
| `integration/test_live_connectivity.py` | Live DB/Redis (`integration` marker) |
| `test_rag_live.py` | Live Gemini (`live_llm` marker, excluded by default) |

---

## Security audit

### Strengths

| Area | Finding |
|------|---------|
| **Authentication** | HS256 JWT; token id in Redis; logout invalidates; fail-closed if Redis unavailable for auth paths |
| **Passwords** | Argon2 via `argon2-cffi` |
| **RBAC** | Permissions derived server-side from `MemberRole`; never from client payload |
| **Tenant isolation** | `X-Store-ID` + membership lookup; repositories scope by `store_id`; tests in `test_tenant_isolation.py` |
| **SQL injection** | SQLAlchemy ORM / bound parameters throughout |
| **Uploads** | Extension allow-list, magic-byte checks, basename-only filenames, `resolve_storage_path` anti-traversal |
| **Error disclosure** | Generic `internal_error` on 500; processing errors sanitized (`sanitize_processing_error`) |
| **CORS** | Explicit origins only in production validation; credentials enabled for SPA |
| **Rate limiting** | Auth register/login per-IP in Redis |
| **Audit** | `audit_logs` for security-relevant actions |
| **AI safety** | Eligibility engine has no LLM override; RAG cite-or-abstain; review requires human checkpoint before binding approval |
| **Secrets** | `.env` gitignored; production rejects short JWT secret; tests use dedicated DB/Redis DB 15 |

### Residual risks & limitations

| Area | Risk | Mitigation / note |
|------|------|-------------------|
| **Fulfillment idempotency** | Concurrent duplicate requests with same key may race before row insert | Unique constraints + retry client; document for integrators |
| **Prompt injection** | Policy chat/user content influences LLM | Grounding + citations; staff-only knowledge manage; mock/default LLM in CI |
| **Rate limiting** | Only auth endpoints limited | Add API-wide limits before public internet exposure |
| **Session storage** | `sessionStorage` tokens | XSS would expose token; keep strict CSP in production hosting |
| **Chroma** | Local filesystem per store | Path under configured `CHROMA_PERSIST_PATH`; not multi-host without shared volume |
| **Background tasks** | Knowledge processing in-process | Restart can leave PROCESSING rows; reprocess endpoint exists |
| **Email/notifications** | Mock rows only | No outbound mail in Phases 8–9 |

---

## Backend consistency review (Phases 1–9)

| Layer | Status |
|-------|--------|
| **Migrations** | `0001`–`0008` linear chain; enum additions for return status and fulfillment tables |
| **API envelope** | Consistent `success` / `error` + `request_id` |
| **Return lifecycle** | Central `ALLOWED_TRANSITIONS`; commerce + fulfillment services call `assert_transition` |
| **Indexes** | FK columns indexed on returns, shipments, refunds, AI review; queue filters use `store_id` + status |
| **Relationships** | `ReturnRequest` → order, customer, items; fulfillment child tables CASCADE on store/return |
| **Analytics** | Aggregations store-scoped; customer endpoint rejects staff roles |

No duplicate router prefixes found. Fulfillment and returns share `/stores/current/returns` prefix by design.

---

## Frontend audit

| Area | Status |
|------|--------|
| Auth | `RequireAuth` / `RequireStore`; token + store in session; 401 clears session |
| Routing | React Router 7; store-gated commerce routes |
| API | Axios interceptors; `X-Store-ID`, `X-Request-ID`; fulfillment sends `Idempotency-Key` |
| Errors | `ApiError` with user-facing messages |
| Loading / empty | Spinner + `EmptyState` on list/detail/dashboard pages |
| Responsive | Tailwind layouts; sidebar drawer on small screens |
| Accessibility | Chart figures with captions/sr-only values; focus rings on controls |
| **Tests** | None automated — **known limitation** |

---

## Known limitations (product)

- Mock payment and carrier integrations only  
- LangGraph + RAG use mock providers in CI  
- AI recommends; humans approve; no auto-refund  
- Analytics AI-vs-outcome chart depends on review runs with finalization payload  
- Sample commerce helper disabled in production  

---

## Remaining release blockers checklist

- [ ] Run full `pytest` against migrated `returnflow_test`  
- [ ] Set production secrets and CORS  
- [ ] Choose hosting for API, Postgres, Redis, Chroma volume  
- [ ] Optional: add Vitest/Playwright for frontend regression  
- [ ] Optional: API rate limits beyond auth  
- [ ] Optional: outbound notification provider (post–Phase 10)

---

## Bug list (historical / open)

| ID | Status | Description |
|----|--------|-------------|
| P10-001 | **Fixed** | CORS `Idempotency-Key` |
| P10-002 | **Fixed** | Default pytest excludes `live_llm` |
| — | **Open** | Fulfillment concurrent idempotency race (low) |
| — | **Open** | No frontend automated tests |

Phase 11 not started.