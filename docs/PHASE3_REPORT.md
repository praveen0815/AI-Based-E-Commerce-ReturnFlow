# Phase 3 validation report

Phase 3 adds orders, order lines, return requests, return lines, and return status history on top of Phase 1 and Phase 2. Phase 4 was not started.

## Database

Migration `0003_commerce` revises `0002_auth`. It creates PostgreSQL enums for order status, payment status, return status, and requested resolution, then tables:

| Table | Purpose |
| --- | --- |
| `products` | Store catalog SKU and name |
| `orders` | Order header with customer, amounts, window, `is_sample` flag |
| `order_items` | Line quantity, price, SKU, JSON metadata |
| `return_requests` | Return header, resolution, window, optional internal notes |
| `return_items` | Quantities returned per order line |
| `return_status_history` | Append-only timeline with actor |

Verified `alembic_version` is `0003_commerce` on `returnflow` and `returnflow_test`.

## Authorization

New permissions:

| Permission | Typical use |
| --- | --- |
| `order:read` | Staff list/search all store orders |
| `order:read_own` | Customers see only their orders |
| `return:read` | Staff list returns for the store |
| `return:read_own` | Customers see their returns |
| `return:create` | Customers open a return on a fulfilled own order |
| `return:manage` | Staff queue, status changes, internal notes |

Store scope still comes from verified `X-Store-ID` membership. Cross-tenant order and return IDs return 404 or 403 as appropriate.

## Return lifecycle

`app/core/return_lifecycle.py` defines allowed transitions. Invalid moves return `invalid_return_transition` (409). Customers may cancel from `REQUESTED` or `UNDER_REVIEW`. Staff advance the workflow server-side.

Main path:

`REQUESTED → UNDER_REVIEW → APPROVED → RETURN_IN_TRANSIT → RECEIVED → REFUND_PROCESSING → COMPLETED`

Also supported: `REJECTED`, `CANCELLED`, `EXCHANGE_PROCESSING` with explicit edges.

## APIs (under `/api/v1/stores/current`)

| Area | Routes |
| --- | --- |
| Orders | `GET /orders`, `/orders/me`, `/orders/search`, `/orders/{id}` |
| Returns | `GET/POST /returns`, `GET /returns/queue`, `GET /returns/{id}`, `GET /returns/{id}/history`, `POST /returns/{id}/cancel`, `PATCH /returns/{id}/status` |
| Development | `POST /dev/sample-commerce` (owner only, `development`/`test`, `is_sample=true`) |

List endpoints support pagination (`page`, `page_size`), sorting, filters, and search where noted.

## Frontend

New routes:

- `/orders`, `/orders/:orderId`, `/orders/:orderId/return`
- `/returns`, `/returns/:returnId`, `/returns/queue`

Role-aware navigation shows Orders and Returns for customers and staff. Return queue appears for `return:manage`. Activity links into these views instead of placeholder copy.

Owners in development can load labeled sample commerce from the Orders screen. Sample rows carry `is_sample` in the API and UI.

## Validation

From `backend` with Compose running and migrations applied:

```text
.\.venv\Scripts\python -m pytest
```

Result: **72 passed**, 1 warning (Starlette `httpx2`), 15.99s.

New coverage includes:

- `test_return_lifecycle.py` — transition rules
- `test_commerce.py` — staff vs customer order visibility, search, return create/cancel/review, invalid transition, queue, sample flag
- Updated role matrix test for customer order/return permissions

From `frontend`:

```text
npm run build
```

`tsc -b && vite build` succeeded.

## Unresolved

- `pytest` still requires PostgreSQL `returnflow_test` and Redis DB 15 for auth and commerce tests.
- Sample commerce is optional and owner-only; production has no seed endpoint behavior (`APP_ENV=production` blocks it).
- Refunds and carrier labels are status-only; no payment processor integration yet.

## Not started

Phase 4 (AI, carrier automation, payments, notifications) was not implemented.