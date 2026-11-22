# ReturnFlow

ReturnFlow is a returns and refund platform. Phase 1 is the React client, FastAPI service, PostgreSQL, Redis, and local Docker infrastructure. Phase 2 adds accounts, stores, membership roles, and access tokens. Phase 3 adds orders, return requests, and a server-validated return lifecycle. Phase 4 adds per-store policy and knowledge document upload, text extraction, and a knowledge center UI. Phase 5 adds Chroma-backed RAG indexing, semantic search, and a grounded policy assistant (Gemini or mock LLM). Phase 6 adds a hybrid eligibility engine: deterministic policy rules plus optional AI explanations. Phase 7 adds a LangGraph multi-agent return review workflow with persisted runs, agent history, and human approval checkpoints. Phase 8 adds mock refund and return-logistics workflows with idempotent APIs, audit trails, and customer notification records. It does not move real money or contact carriers. Phase 9 adds store admin and customer dashboards backed by analytics APIs, chart views, and enhanced return operations lists. Phase 10 is an integration and security audit: test matrix documentation, security hardening, and deployment readiness notes — see [docs/PHASE10_REPORT.md](docs/PHASE10_REPORT.md). Phase 11 (v0.11.0) adds Docker full-stack deployment, nginx API proxy, persistent volumes, and GitHub release docs — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/PHASE11_REPORT.md](docs/PHASE11_REPORT.md).

## Architecture

```text
Browser (React, TypeScript, Vite, Tailwind)
        |  sessionStorage: access token and selected store id
        |  Authorization: Bearer, X-Store-ID, X-Request-ID
        v
   nginx (Docker full stack)  OR  direct http://localhost:8000 (Vite dev)
        |
FastAPI (Python 3.12)
        |-- PostgreSQL 16   users, stores, orders, returns, knowledge, fulfillment, analytics
        |-- Redis 7         access-token allowlist and auth rate limits
        |-- Volumes       knowledge uploads, Chroma indexes (Docker / data/)
```

The API process can start when PostgreSQL or Redis is down. `GET /api/v1/health` only proves the process is alive. `GET /api/v1/ready` returns 200 when both dependencies answer and 503 when either does not. Dependency failures report an exception type, not a connection string. Authenticated routes fail closed if Redis cannot confirm the token.

### Backend modules

| Module | Responsibility |
| --- | --- |
| `app/core` | Settings, structured logging, error and response envelopes |
| `app/api` | Versioned routes, dependencies, exception handlers |
| `app/database` | Async SQLAlchemy engine and Redis client lifecycle |
| `app/models` | Users, stores, memberships, and append-only audit logs |
| `app/schemas` | Auth, store, membership, and audit payloads |
| `app/services` | Readiness, registration, sessions, stores, and audit writes |
| `app/repositories` | User, store, membership, and audit queries |
| `app/middleware` | Request ids and access logs. Query strings are omitted |
| `alembic` | `0001_baseline` through `0008_fulfillment` |
| `tests` | Foundation tests plus auth, token, role, and tenant checks |

### Frontend modules

| Module | Responsibility |
| --- | --- |
| `components` | Reusable controls, navigation, and status presentation |
| `layouts` | Responsive application shell |
| `pages` | Auth, orders, returns, knowledge center, return queue, profile, members, audit, and foundation screens |
| `services` | Axios client, session storage, and account API |
| `hooks` | Auth state, platform status, local preferences, responsive behavior |
| `types` | API, health, and account payloads |
| `utils` | Class names and display formatting |

### API envelope

Success:

```json
{"success": true, "data": {}, "request_id": "..."}
```

Failure:

```json
{"success": false, "error": {"code": "...", "message": "..."}, "request_id": "..."}
```

Send `X-Request-ID` to correlate a call. The API keeps safe characters and generates an id otherwise. The same id is returned in the header and the body.

## Authentication

Registration and login return a signed access token. The token carries the user id, a token id, and an expiry. It does not carry a store id or a role. Redis stores `auth:session:{token id}` until logout or expiry. A token that is signed but missing from Redis is rejected.

Passwords are hashed with Argon2. Login and registration are rate limited per client address. Failed login uses the same response for an unknown email and a wrong password.

`X-Store-ID` selects among the caller's memberships. The API ignores a store id unless that user is a member. Store queries use the membership loaded on the server. Roles are `OWNER`, `ADMIN`, `MANAGER`, `SUPPORT_AGENT`, and `CUSTOMER`. Permissions are derived from the role in code.

Set `JWT_SECRET` to a unique value of at least 32 characters. Production rejects a missing, short, or placeholder secret. The browser keeps the access token in `sessionStorage` and clears it on logout or when a protected call returns `token_expired` or `not_authenticated`.

## Prerequisites

- Python 3.12
- Node.js 22 or newer
- Docker with Compose v2

## Setup

From `C:\AI-Projects\ReturnFlow`:

```powershell
Copy-Item .env.example .env
```

Edit `.env`. Set `POSTGRES_PASSWORD`, and use that same password in `DATABASE_URL`. The checked-in default `change-me` is a placeholder and will not authenticate.

Run Alembic from `backend` with the `alembic` console script. `python -m alembic` imports the local `backend/alembic` migration package instead of the installed tool.

The API reads the repository-root `.env`. Frontend URLs are public local defaults:

```powershell
Copy-Item frontend\.env.example frontend\.env.local
```

`frontend/.env.local` is gitignored. `npm run dev` and `npm run build` also fall back to `http://localhost:8000` when the variable is absent.

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```

### Frontend

```powershell
cd frontend
npm install
npm run build
```

### PostgreSQL and Redis

From the repository root, after `.env` exists:

```powershell
docker compose up -d
docker compose ps
```

Apply the migrations and start the API:

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Live dependency test, in another shell:

```powershell
cd backend
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python -m pytest -m integration
```

Start the client:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Sign in, create a store, and use the dashboard (live analytics), orders, returns, knowledge, and policy assistant.

## Features (summary)

| Area | What it does |
| --- | --- |
| Auth & tenancy | JWT sessions, store membership, RBAC |
| Returns | Lifecycle, queue, eligibility, AI review, mock fulfillment |
| Knowledge & RAG | Upload policies, Chroma search, grounded chat |
| Analytics | Admin KPIs/charts and customer dashboard |
| Security | Tenant isolation, audit log, rate-limited auth |

Default AI and fulfillment integrations are **mock** unless you configure Gemini and real providers yourself.

## Docker

**Infrastructure only** (local `uvicorn` + `npm run dev`):

```powershell
docker compose up -d postgres redis
```

**Full stack** (API + SPA + migrations on start + persistent knowledge/Chroma):

```powershell
docker compose --profile full build
docker compose --profile full up -d
```

| URL | Purpose |
| --- | --- |
| http://localhost:8080 | Web UI (nginx → API `/api/*`) |
| http://localhost:8000/api/v1/health | Liveness |
| http://localhost:8000/api/v1/ready | Postgres + Redis |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for volumes, env overrides, smoke tests, and production notes. Build images manually if needed: `docker build -t returnflow-api ./backend` and `docker build -t returnflow-web ./frontend` (Compose uses the same Dockerfiles).

## Environment variables

Copy `.env.example` to `.env`. Never commit `.env`. Key values: `JWT_SECRET` (≥32 chars), `POSTGRES_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS`, `LLM_PROVIDER`, `RAG_EMBEDDINGS_PROVIDER`, optional `GEMINI_API_KEY`.

## Screenshots

Add UI captures under `docs/screenshots/` after you run the smoke checklist in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The repository does not ship screenshots by default.

## Limitations

- Mock refund and shipping; no outbound email  
- Policy chat and AI review use mock LLM by default (`LLM_PROVIDER=mock`)  
- No frontend E2E test suite in CI  
- Live Gemini / sentence-transformers require extra setup and are optional  

## Useful endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service name and probe links |
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/ready` | PostgreSQL and Redis readiness |
| GET | `/api/docs` | OpenAPI UI outside production |
| POST | `/api/v1/auth/register` | Create an account and a session |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/logout` | Invalidate the current access token |
| GET | `/api/v1/auth/me` | Current user and memberships |
| GET, PATCH | `/api/v1/profile` | Account display name |
| GET, POST | `/api/v1/stores` | List memberships or create a store |
| GET, PATCH | `/api/v1/stores/current` | Read or rename the selected store |
| GET, POST | `/api/v1/stores/current/members` | List or add members |
| PATCH, DELETE | `/api/v1/stores/current/members/{id}` | Change a role or remove a member |
| GET | `/api/v1/stores/current/audit` | Store-scoped security events |
| GET | `/api/v1/stores/current/orders` | Paginated store or own orders |
| GET | `/api/v1/stores/current/orders/search` | Search by order number or customer |
| GET | `/api/v1/stores/current/orders/{id}` | Order detail and lines |
| GET, POST | `/api/v1/stores/current/returns` | List or create return requests |
| GET | `/api/v1/stores/current/returns/queue` | Open returns for staff |
| PATCH | `/api/v1/stores/current/returns/{id}/status` | Validated status change |
| POST | `/api/v1/stores/current/dev/sample-commerce` | Labeled dev sample data only |
| GET, POST | `/api/v1/stores/current/knowledge/documents` | List or upload policy documents |
| GET, DELETE | `/api/v1/stores/current/knowledge/documents/{id}` | Document detail or delete |
| POST | `/api/v1/stores/current/knowledge/documents/{id}/reprocess` | Re-run text extraction |
| POST | `/api/v1/stores/current/knowledge/rag/index` | Index or reindex documents into Chroma |
| POST | `/api/v1/stores/current/knowledge/rag/reindex` | Reindex all processed documents |
| DELETE | `/api/v1/stores/current/knowledge/rag/index` | Drop vectors for store or one document |
| POST | `/api/v1/stores/current/knowledge/rag/search` | Semantic policy search |
| POST | `/api/v1/stores/current/knowledge/rag/ask` | Grounded policy Q&A with citations |
| GET | `/api/v1/stores/current/knowledge/rag/sources` | Source document metadata |
| POST | `/api/v1/stores/current/knowledge/rag/feedback` | Policy assistant feedback |
| POST | `/api/v1/stores/current/returns/eligibility/evaluate` | Deterministic eligibility check |
| GET | `/api/v1/stores/current/returns/eligibility/{id}` | Eligibility decision detail |
| POST | `/api/v1/stores/current/returns/eligibility/{id}/explain` | AI summary (non-binding) |
| POST | `/api/v1/stores/current/returns/eligibility/{id}/request-review` | Escalate to human review |
| GET, PUT | `/api/v1/stores/current/returns/policy-rules` | Read or publish rule versions |
| GET | `/api/v1/stores/current/returns/{id}/eligibility` | Latest decision for a return |
| POST | `/api/v1/stores/current/returns/{id}/ai-review` | Start LangGraph AI review |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/latest` | Latest review run |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}` | Review status |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/events` | Agent event history |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/output` | Structured output |
| POST | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/resume` | Human checkpoint |
| GET | `/api/v1/stores/current/returns/{id}/fulfillment` | Shipment, refund, timeline, notifications |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/label` | Request mock return label (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/shipment/in-transit` | Mark in transit (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/shipment/received` | Mark received (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/refund` | Initiate mock refund (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/refund/finalize` | Complete mock refund (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/exchange` | Start exchange fulfillment (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/complete` | Close return case |
| GET | `/api/v1/stores/current/analytics/admin` | Store KPIs and charts (`days` query) |
| GET | `/api/v1/stores/current/analytics/me` | Customer dashboard metrics |

Production mode (`APP_ENV=production`) disables the API docs, rejects `DEBUG=true`, rejects a short or placeholder `JWT_SECRET`, and blocks the sample-commerce helper.

## Tests

`pytest` covers settings, health, request ids, CORS, error envelopes, logging, mocked probes, and the auth suite. The auth tests use PostgreSQL database `returnflow_test` and Redis database 15. Create that database, run `alembic upgrade head` against it, and keep Compose running before `pytest`. Redis database 0 is not flushed.

`RUN_INTEGRATION=1 pytest -m integration` checks a real `SELECT 1` and `PING` after Compose is healthy.

Phase reports: [docs/PHASE1_REPORT.md](docs/PHASE1_REPORT.md) through [docs/PHASE11_REPORT.md](docs/PHASE11_REPORT.md).  
Release checklist: [docs/GITHUB_RELEASE_CHECKLIST.md](docs/GITHUB_RELEASE_CHECKLIST.md).

## Deployment readiness

- Run `pytest` with Docker Postgres/Redis and migrated `returnflow_test` (see Phase 10 report).
- Configure production `JWT_SECRET`, `CORS_ORIGINS`, and database credentials.
- Frontend: `npm run build`; full stack: `docker compose --profile full up -d`.
