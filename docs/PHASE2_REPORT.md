# Phase 2 validation report

Phase 2 adds accounts, stores, memberships, and role checks on the Phase 1 application. Return processing and AI calls were not added.

## What was implemented

Access tokens are HS256 JWTs. The claims are the user id (`sub`), a token id (`jti`), and the issued/expiry times. The token does not contain a store id or a role. Redis keeps `auth:session:{jti}` for the token lifetime. Logout deletes that key, so the token is rejected before it expires. A Redis failure on login, logout, or token lookup returns `auth_backend_unavailable` and does not accept the token.

Passwords are hashed with Argon2. The hash is never returned by the API. Login uses one `invalid_credentials` response for an unknown email and a wrong password. Registration of a duplicate email returns `email_taken`. Login and registration are rate limited in Redis per client address.

A request may send `X-Store-ID`. The API accepts it only when the authenticated user has a membership for that store. With one membership and no header, that membership is used. With several memberships and no header, the API returns `store_selection_required`. Another tenant's store id returns `store_forbidden` and does not include that store's name. Member and audit queries filter on the verified store id.

Roles are `OWNER`, `ADMIN`, `MANAGER`, `SUPPORT_AGENT`, and `CUSTOMER`. Permissions are a code map, not a database table:

| Role | Permissions |
| --- | --- |
| OWNER | store read/update, membership read/manage, audit read |
| ADMIN | the same, except an admin cannot assign or change an owner |
| MANAGER | store read, membership read, audit read |
| SUPPORT_AGENT | store read, membership read |
| CUSTOMER | store read |

The last owner of a store cannot be demoted or removed. A member can be added only when that email already belongs to an active account. Store slugs are generated on the server.

Security-sensitive actions write an audit row. Detail keys for passwords, tokens, and secrets are dropped before insert. Store audit lists are limited to that store, so login events (which have no store) do not appear there. Access logs record the method, path, and status. They do not record the query string, the bearer token, or the password. Unexpected errors return `internal_error` without a stack trace. Validation errors do not echo the submitted password.

The browser stores the access token and the selected store id in `sessionStorage`. Protected screens redirect to sign-in. A protected call that returns `token_expired` or `not_authenticated` clears the session and shows a session-expired message. A login failure does not clear a session, because that response is `invalid_credentials`. Navigation shows Members only for `membership:read` and Audit only for `audit:read`.

## Database

Migration `0002_auth` revises `0001_baseline`. It creates `store_member_role` and the tables `users`, `stores`, `store_memberships`, and `audit_logs`, with unique constraints, foreign keys, indexes, and timestamps. Application code generates the UUIDs.

Verified versions:

| Database | `alembic_version` |
| --- | --- |
| `returnflow` | `0002_auth` |
| `returnflow_test` | `0002_auth` |

`returnflow_test` is used only by the auth tests. Those tests flush Redis database 15 and refuse to flush any other Redis database. They truncate the four auth tables after connecting to `returnflow_test`.

## Commands and results

From `backend`, with Compose up:

```text
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest
```

`pytest` result: **65 passed**, 3 warnings, 10.93s.

The 65 include the live PostgreSQL and Redis probe because `RUN_INTEGRATION=1` was already set in the shell. A second run of the auth, token, permission, and tenant files reported **24 passed**.

Warnings:

- Starlette reports that `TestClient` wants `httpx2` instead of `httpx`. Existing behavior. Tests still passed.
- SQLAlchemy 2.1 deprecates `Result.tuples()`. The audit query now unpacks rows directly. The follow-up auth run did not repeat that warning.

Frontend, from `frontend`:

```text
npm run build
```

`tsc -b && vite build` completed. The production bundle is `dist/assets/index-DGDGAD3B.js` (369.00 kB, gzip 118.01 kB) and `dist/assets/index-DgeVFMZy.css`.

Browser checks used the production preview at `http://127.0.0.1:4173` and the API at `http://127.0.0.1:8000`, headless Edge:

- An anonymous visit to `/` and `/members` lands on sign-in.
- Registration rejects a 5-character password in the form.
- Registration continues to store onboarding. Members and Audit stay hidden until a store exists.
- The owner sees Members and Audit, can save a profile name, sign out, and add an existing account as a customer.
- The customer does not see Members or Audit. Opening `/audit` shows the permission error.
- Replacing the stored access token and reloading shows "Your session expired".
- At 390px width, the menu starts off-canvas, opens Members, and closes after navigation.

The API access log for that session has no password and no `eyJ` token prefix.

A local `JWT_SECRET` of 64 characters was written to the gitignored `.env` because the previous value was a placeholder. It was not printed and it is not in git.

## Security behavior covered by tests

- Argon2 hash stored, plaintext password absent from the response and the log.
- Logout, expiry, a bad signature, and a missing Redis session each reject the token.
- Customer, support, manager, and admin limits, including the last-owner rule.
- A store id for another tenant, a membership id from another store, and a store id in the JSON body cannot read or change the other tenant.
- Audit details drop password and token fields.

## Unresolved

- `pytest` now needs PostgreSQL (`returnflow_test`) and Redis database 15. The Phase 1 suite could run without Docker. The foundation tests still mock readiness, but importing the auth tests connects to those services.
- The access token lives for `ACCESS_TOKEN_TTL_SECONDS` (default 900). There is no refresh token. The client treats expiry as a new sign-in.
- The Starlette `httpx` / `httpx2` warning remains.

## Not started

Phase 3 was not started. There are still no return, refund, policy, or shipment tables, no payment calls, and no AI provider.
