# Phase 6 report — eligibility and decision engine

## Scope delivered

- Versioned `store_return_policy_rules` evaluated entirely in Python
- Structured outcomes: `ELIGIBLE`, `INELIGIBLE`, `NEEDS_REVIEW` with codes, policy references, missing fields, and next steps
- Append-only `return_eligibility_decisions` audit rows
- AI layer generates optional summaries only; cannot override deterministic outcomes
- APIs under `/stores/current/returns/eligibility/*` and policy rule management
- Return create and return detail UI with eligibility panel, human review request, and AI summary

## Verification

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_eligibility.py -q
```