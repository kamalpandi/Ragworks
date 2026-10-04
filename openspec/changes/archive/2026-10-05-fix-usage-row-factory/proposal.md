## Why

Two psycopg call sites open a default (tuple) cursor but then read columns by name, so any request whose `usage_logs` table has data raises `TypeError: tuple indices must be integers or slices, not str`. On a populated database `GET /ui/dashboard/stats` (via `GET /api/v1/dashboard`) and `GET /api/v1/usage` return HTTP 500. The bug shipped because the migration's manual checklist ran every fragment against an **empty** `usage_logs` table: `fetchall()` returns `[]`, the loop never executes, no error surfaces, and the fragment renders an empty panel as `200` (`2026-10-04-separate-ui-from-backend/tasks.md:57`).

## What Changes

- Fix `app/services/dashboard_service.py:76` (`get_usage_stats`) to open its cursor with `row_factory=dict_row`, matching the column-name access used at lines 87-92.
- Fix `app/api/v1/endpoints/usage.py:21` (`GET /api/v1/usage`) the same way; it has the identical latent defect and would 500 on the first populated request.
- Document the deliberate resilience boundary at `_DB_ERRORS` in `dashboard_service.py`: infrastructure failures (`PsycopgError`, `OSError`, `RuntimeError`) degrade to zero-stats so the dashboard still renders; programming errors (`TypeError`, `AttributeError`, `KeyError`) are **not** caught and must surface as 500s. This captures the decision to fix the row factory rather than widen the caught exception set.
- Replace the empty `TestUsageTracking` stubs (`tests/test_multi_user_rag.py:130-141`) with real integration tests that seed `usage_logs` and assert aggregation and HTTP status for both endpoints.
- Add an AST guard to `tests/test_architecture.py`: any `conn.cursor()` call whose result is indexed by a string literal (`row["..."])` must pass `row_factory=dict_row`. This catches the next instance deterministically, without Postgres.
- Amend the UAT checklist so fragment/page checks **require seeded usage data as a precondition** (≥1 query + ≥1 ingest row), closing the empty-table false-pass that hid this.

No behavior, schema, or API-shape change: the specs `usage-tracking` and `dashboard-api` already specify both endpoints and their aggregation; this restores the implementation to the behavior they describe.

## Capabilities

### New Capabilities
<!-- none; no new behavior -->

### Modified Capabilities
<!-- none; existing requirements are restored, not changed. skip_specs: true -->

## Impact

- **Code**: `app/services/dashboard_service.py` (cursor factory + `_DB_ERRORS` comment), `app/api/v1/endpoints/usage.py` (cursor factory), `tests/test_multi_user_rag.py` (real tests), `tests/test_architecture.py` (guard).
- **APIs**: `GET /api/v1/usage` and `GET /api/v1/dashboard` / `GET /ui/dashboard/stats` fixed from 500 to correct aggregation on populated data. Response shape unchanged.
- **Specs**: none. `skip_specs: true`; this is a pure implementation fix.
- **Data / dependencies**: none. No migration, no new package.
