# Phase 8 report — Refund & return logistics (mock)

## Scope delivered

- Extended return lifecycle: `LABEL_PENDING` → `LABEL_GENERATED` → `RETURN_IN_TRANSIT` → `RECEIVED` → `REFUND_PENDING` → `REFUND_COMPLETED` → `COMPLETED`
- Provider protocols plus **mock-only** refund and logistics implementations (no real money or carriers)
- Tables: `return_shipments`, `return_refunds`, `return_notification_events`, `fulfillment_idempotency`
- Idempotent fulfillment POSTs via `Idempotency-Key` header and persisted response bodies
- Mock customer email events (stored, not sent) and audit actions on each step
- Return detail UI: refund timeline, tracking, label link, refund status, admin actions, notification history
- Exchange path: received → `EXCHANGE_PROCESSING` without refund initiation

## Verification

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic upgrade head
$env:DATABASE_URL = "postgresql+asyncpg://returnflow:returnflow_local_dev@localhost:5432/returnflow_test"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_fulfillment.py -q
cd ..\frontend
npm run build
```

Mock failure triggers: include `fail-label` or `fail-refund` in the idempotency key string.

## Not in this phase

- Real payment providers, carrier APIs, or Phase 9 work