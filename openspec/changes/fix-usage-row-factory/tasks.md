## 1. Fix cursor row factories

- [x] 1.1 In `app/services/dashboard_service.py`, import `from psycopg.rows import dict_row` and change the `get_usage_stats` cursor to `conn.cursor(row_factory=dict_row)`. Done: fixed at line ~81; `test_dashboard_endpoint_populated_returns_stats` and `test_usage_logs_created_after_query` pass
- [x] 1.2 In `app/api/v1/endpoints/usage.py`, import `from psycopg.rows import dict_row` and change the cursor to `conn.cursor(row_factory=dict_row)`. Done: fixed at line ~22; `test_usage_endpoint_returns_correct_aggregation` passes
- [x] 1.3 Add a comment at `_DB_ERRORS` stating infrastructure failures degrade to zero-stats while programming errors (`TypeError`, `AttributeError`, `KeyError`) are intentionally not caught and surface as 500s. Done: comment added; `TypeError` remains absent from the tuple

## 2. Regression tests

- [x] 2.1 Replace the `TestUsageTracking` stubs in `tests/test_multi_user_rag.py` with real integration tests that seed `usage_logs` and assert per-operation counts, token/chunk totals, tenant scoping, and HTTP `200` for `/api/v1/usage` and `/api/v1/dashboard`. Done: 5 tests pass against live PGVector (write path, API aggregation, dashboard, query-only, ingest-only)
- [x] 2.2 Add an AST guard to `tests/test_architecture.py`: any `conn.cursor()` in `app/` indexed by a string literal without `row_factory=dict_row` is a violation. Done: guard passes on the clean tree and `test_row_factory_guard_detects_injected_violation` fails on an injected violation

## 3. Verification

- [x] 3.1 Require seeded usage data as a precondition for page/fragment checks in a durable checklist. Done: added `docs/uat-checklist.md` (≥1 query + ≥1 ingest `usage_logs` row) and a pointer from `AGENTS.md`
- [x] 3.2 Run the populated path in three passes — both operations, query-only, ingest-only. Done: automated as `test_usage_endpoint_returns_correct_aggregation`, `test_query_only_aggregation`, `test_ingest_only_aggregation`; all pass
- [x] 3.3 Re-confirm the cursor sweep: `rg -n "conn\.cursor\(\)" app` shows only the known-safe sites (insert-only, positional, or connection-level dict); neither fixed file appears. Done: verified
- [x] 3.4 Run `ruff check . && ruff format .` and `pytest`. Done: `ruff check` clean, `ruff format --check` clean (186 files), 39 tests pass
