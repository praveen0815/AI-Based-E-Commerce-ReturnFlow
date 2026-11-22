# Phase 9 report — Admin dashboard & analytics

## Scope delivered

- `GET /api/v1/stores/current/analytics/admin` — KPIs and chart series from PostgreSQL (staff `return:read`)
- `GET /api/v1/stores/current/analytics/me` — customer dashboard metrics (`return:read_own`, customers only)
- KPIs: orders, returns, pending review, approved, rejected, completed refunds, refund value, return rate
- Charts: returns over time, reasons, status distribution, refund amounts, product frequency, processing duration, AI vs outcome
- Overview and activity pages use live API data (sample metrics removed from overview)
- Return queue and returns list: search, status filter, sort, pagination
- Return detail: quick approve/reject for staff; existing eligibility, AI review, and fulfillment panels unchanged

## Verification

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_analytics.py -q
cd ..\frontend
npm run build
```

## Not in this phase

- Phase 10 or external BI exports