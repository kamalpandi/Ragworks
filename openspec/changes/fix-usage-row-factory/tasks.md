## 1. Fix cursor row factories

- [ ] 1.1 In `app/services/dashboard_service.py`, import `from psycopg.rows import dict_row` and change the `get_usage_stats` cursor (line ~76) to `conn.cursor(row_factory=dict_row)`; verify `get_usage_stats` returns non-zero counts for a tenant with seeded rows via the 2.1 integration test
- [ ] 1.2 In `app/api/v1/endpoints/usage.py`, import `from psycopg.rows import dict_row` and change the cursor (line ~21) to `conn.cursor(row_factory=dict_row)`; verify `GET /api/v1/usage` returns `200` with populated `usage_logs` via the 2.1 integration test
- [ ] 1.3 Add a comment at `_DB_ERRORS` in `app/services/dashboard_service.py` stating that infrastructure failures (`PsycopgError`, `OSError`, `RuntimeError`) degrade to zero-stats while programming errors (`TypeError`, `AttributeError`, `KeyError`) are intentionally not caught and surface as 500s; verify the comment is present and `TypeError` is absent from the tuple

## 2. Regression tests

- [ ] 2.1 Replace the `TestUsageTracking` stubs in `tests/test_multi_user_rag.py` (lines 130-141) with real integration tests that seed `usage_logs` for a tenant and assert: `GET /api/v1/usage` returns `200` with correct per-operation counts and totals; `GET /ui/dashboard/stats` returns `200`; aggregation is tenant-scoped. Verify with `pytest tests/test_multi_user_rag.py -k UsageTracking` against a running PGVector instance
- [ ] 2.2 Add an AST guard to `tests/test_architecture.py`: any `conn.cursor()` call in `app/` whose result is indexed by a string literal (`row["..."]`) in the same scope must pass `row_factory=dict_row`; verify it passes on the clean tree and fails on an injected `conn.cursor()` + `row["x"]` violation

## 3. Verification

- [ ] 3.1 Amend the UAT checklist so page/fragment checks require seeded usage data as a precondition (≥1 query + ≥1 ingest `usage_logs` row) before asserting `200`; verify the checklist states the precondition (note for the current checklist, and the pattern for future changes)
- [ ] 3.2 Run UAT on the populated path in three passes — both operations present, query-only, and ingest-only — confirming `GET /ui/dashboard/stats` and `GET /api/v1/usage` return `200` and correct numbers in every pass (the ingest-only pass covers the `elif` / `chunks` alias)
- [ ] 3.3 Run `rg -n "conn\.cursor\(\)" app` and confirm the only remaining factory-less cursors are the known-safe sites (insert-only, positional, or connection-level dict); verify neither fixed file appears in the list
- [ ] 3.4 Run `ruff check . && ruff format .` and `pytest` (including the new architecture guard); verify all pass
