## Context

See `proposal.md` for motivation. Current-state facts that shape the approach:

- `psycopg` cursors default to tuple rows. Reading a column by name requires `row_factory=dict_row`.
- The repo's convention is explicit per-cursor opt-in: `conversation_service.py:30,58`, `api_key_manager.py:40`, and `pgvector_db.py:102,120` pass `row_factory=dict_row`; `log_store.py` sets it at connection level (`log_store.py:36-40`).
- A mechanical sweep of `conn.cursor()` across `app/` found exactly two sites that read by name without the factory:
  - `app/services/dashboard_service.py:76` (accessed at `:87-92`)
  - `app/api/v1/endpoints/usage.py:21` (accessed at `:49-64`)
  Every other factory-less cursor is insert-only, positional, or connection-level dict. No third straggler.
- `get_usage_stats` catches `_DB_ERRORS = (PsycopgError, OSError, RuntimeError)` (`dashboard_service.py:15,93`); `TypeError` is not in that set, so the bug escapes the service and becomes a 500.
- The archived migration's verification (`2026-10-04-separate-ui-from-backend/tasks.md:57`) exercised fragments against an empty `usage_logs`; the populated path was never run.

## Goals / Non-Goals

**Goals:**
- Both `usage_logs` read paths work against populated data and match the existing `usage-tracking` / `dashboard-api` specs.
- A deterministic, DB-free guard prevents this bug class from recurring.
- The resilience policy around `_DB_ERRORS` is explicit in code so the next reader does not "fix" it by catching `TypeError`.

**Non-Goals:**
- Auditing or refactoring the other (correct) cursor call sites.
- Changing API response shapes, specs, or the database.
- Introducing a shared helper/connection-level default — see D1.

## Decisions

### D1: Per-cursor `row_factory=dict_row` at the two sites

Pass `row_factory=dict_row` on the two cursors and import `from psycopg.rows import dict_row`.

- **Why**: matches the established repo convention and confines the change to the two broken sites.
- **Alternatives**:
  - **Pool/connection-wide default** (`AsyncConnectionPool(..., kwargs={"row_factory": dict_row})`): rejected — `get_status` relies on positional `row[0]` (`dashboard_service.py:43,51`), which breaks under dict rows; it also silently changes global behavior.
  - **Switch access to positional indices** (`row[0]`, `row[1]`): rejected — diverges from convention and is brittle to column reordering.

### D2: Keep `_DB_ERRORS` as-is; document the resilience boundary

Do **not** add `TypeError` to the caught set. Add a comment at the definition stating that infrastructure failures degrade to zero-stats while programming errors (`TypeError`, `AttributeError`, `KeyError`) propagate as 500s.

- **Why**: `_DB_ERRORS` is a resilience policy, not a catch-all. Catching `TypeError` would hide the wrong-row-factory bug permanently (zero stats, no log) instead of fixing it. Programming errors are bugs and should be loud.
- **Alternatives**: widen `_DB_ERRORS` — rejected, it would have masked this bug and every future one of the same shape.

### D3: Real integration tests plus an architecture guard (no mocked unit test)

- **Integration tests (primary)**: seed `usage_logs` for a tenant, then call `get_usage_stats`, `GET /api/v1/usage`, and `GET /ui/dashboard/stats`; assert counts, token/chunk totals, tenant scoping, and HTTP `200` (the regression signal for the 500).
- **AST guard**: extend `tests/test_architecture.py` to flag any `conn.cursor()` call in `app/` whose scope indexes a result by string literal without `row_factory=dict_row`.
- **Rejected — mocked unit test**: a test that fakes the cursor and returns dicts encodes the fix rather than detecting the bug; reverting line 76 to `conn.cursor()` would still pass because the mock does not enforce the requested factory. It tests the mock, not the code.
- **Guard caveat**: the AST check is a heuristic on the common shape (same-scope `row["..."]` after `conn.cursor()`). It will miss an aliased cursor indexed in another function. Accepted — it catches both real instances and the shape future authors will copy.

## Risks / Trade-offs

- **AST guard false negatives** (aliased/later-indexed cursors) → Mitigation: the integration tests are the behavioral catch-all; the guard is the cheap early warning, not the sole defense.
- **Integration tests require a running Postgres** → Mitigation: they live with the existing `TestMultiTenancy`/`TestUsageTracking` integration suite that already declares "Requires PGVector to be running"; unit/architecture suites continue to run without a DB.
- **A second bug hides behind the first in the `ingest` branch** (the `elif` / `chunks` alias) → Mitigation: UAT runs the populated path in three passes: both operations present, query-only, and ingest-only.
- **`skip_specs: true` could be read as "untested behavior"** → Mitigation: `usage-tracking` and `dashboard-api` already specify both endpoints; this change restores them, so there is genuinely no spec delta to write.
