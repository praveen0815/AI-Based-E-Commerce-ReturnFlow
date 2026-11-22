# Phase 1 validation report

Date: 2026-11-21

Phase 1 is the ReturnFlow foundation: a FastAPI service, a React dashboard, PostgreSQL 16, Redis 7, and local Docker files. It does not process returns and it does not call an AI provider.

## Results

| Check | Result |
| --- | --- |
| Backend install on Python 3.12 | Passed |
| `pytest` | 38 passed, 1 skipped, 1 warning |
| Live connectivity test | 1 passed |
| Frontend install and `npm run build` | Passed |
| PostgreSQL 16 and Redis 7 | Healthy |
| Alembic baseline | `0001_baseline` applied |
| `GET /api/v1/health` | 200, liveness envelope |
| `GET /api/v1/ready` | 200, PostgreSQL and Redis up |
| Responsive UI | Passed in headless Edge at 1280px and 390px |
| `docker build` API and web images | Passed (`returnflow-api`, `returnflow-web`) |

The skipped default test is the live PostgreSQL/Redis probe. It runs when `RUN_INTEGRATION=1`.

## Commands

```powershell
cd C:\AI-Projects\ReturnFlow\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest -q

cd C:\AI-Projects\ReturnFlow\frontend
npm install
npm run build

cd C:\AI-Projects\ReturnFlow
docker compose --env-file .env up -d
docker exec returnflow-postgres pg_isready -U returnflow -d returnflow
docker exec returnflow-postgres psql -U returnflow -d returnflow -c "SELECT version_num FROM alembic_version;"
docker exec returnflow-redis redis-cli ping

cd C:\AI-Projects\ReturnFlow\backend
.\.venv\Scripts\alembic upgrade head
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python -m pytest -m integration -q
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use the Alembic console script. `python -m alembic` from `backend` loads the local migration folder instead of the installed Alembic package.

## Endpoint evidence

`GET /api/v1/health` with `X-Request-ID: phase1-health`:

```json
{"success":true,"data":{"status":"ok","service":"ReturnFlow","environment":"development","version":"0.1.0"},"request_id":"phase1-health"}
```

`GET /api/v1/ready` with `X-Request-ID: phase1-ready`:

```json
{"success":true,"data":{"status":"ready","checks":{"database":{"status":"up"},"redis":{"status":"up"}}},"request_id":"phase1-ready"}
```

PostgreSQL reported `accepting connections`. Redis answered `PONG`. Alembic's version table contains `0001_baseline`.

## UI evidence

Headless Edge exercised the production preview at `http://127.0.0.1:4173` against the live API.

Passed at 1280px:

- Sidebar is visible and the mobile menu button is hidden.
- Sample metrics are labeled Sample.
- The status card reports that the API, PostgreSQL, and Redis are reachable.
- Live return activity is empty.
- The notification panel is empty.
- The preferences form shows field errors, then a success message, and updates the local profile.
- Hiding sample metrics replaces them with an empty state.
- An unknown route shows the Phase 1 not-found state.

Passed at 390px:

- Content stacks in one column.
- The menu button is visible and the sidebar starts off-canvas.
- Opening the menu shows the drawer. Choosing a link closes it.

## Warning

Pytest prints one Starlette deprecation warning: the bundled `TestClient` import path prefers `httpx2`. The suite still passes. No application behavior depends on that warning.

## Local files that are not source

`.env` is gitignored and was created so Compose and the API share one local database password. Replace that password before this stack is shared or deployed. `frontend/node_modules`, `frontend/dist`, and `backend/.venv` are generated.

## Not started

Phase 2 was not started. There is no return or refund schema, no authentication, and no AI client.
