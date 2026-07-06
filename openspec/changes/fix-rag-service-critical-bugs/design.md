## Context

The `multi-user-rag-service` change added multi-tenancy, authentication, rate limiting, connection pooling, LLM concurrency, conversation memory, and usage tracking. An architectural audit found 3 critical bugs, 3 high-severity issues, and 8 medium quality issues. These are concentrated in the LLM queue system, database migration SQL, API response models, and middleware logic.

No new dependencies or architectural patterns are needed. All fixes are local to specific files.

## Goals / Non-Goals

**Goals:**
- Fix the 3 critical bugs so the system can start and function
- Fix the 3 high-severity issues so conversation memory and auth work correctly
- Fix the medium-severity issues that affect correctness or hygiene
- Keep changes minimal and surgical

**Non-Goals:**
- Redesigning the LLM queue architecture
- Adding Redis for rate limiting
- Refactoring the auth middleware flow
- Adding new features beyond `/health`
- Writing new tests (test stubs already exist)

## Decisions

### 1. Queue Start: Call `start()` in `_get_queue()`

**Chosen**: Add `await _llm_queue.start()` after creating the queue instance in `_get_queue()`. This is the simplest fix — one line.

The `_get_queue()` function is currently synchronous but needs to call an async `start()`. Change it to an async factory: rename `_get_queue()` to `async _ensure_queue()` and call it with `await` from the call sites.

**Alternatives considered**:
- Start in `LlamaCppProvider.__init__()`: Would work but provider init is synchronous, and queue start is async. Would need `asyncio.create_task` in a sync context — fragile.
- Start in lifespan: Would couple the queue lifecycle to FastAPI lifespan, which is fragile if the provider is created before the lifespan runs.

### 2. Migration SQL Fix: `Literal` instead of `Identifier`

**Chosen**: Import `Literal` from `psycopg.sql` and use `Literal(self.table_name)` for the `WHERE table_name = ...` comparison in the migration's `IF NOT EXISTS` block. The `ALTER TABLE` line correctly uses `Identifier` (it's a DDL identifier), so only the WHERE clause changes.

### 3. Streaming Fix: Restore original chunk-by-chunk pattern

**Chosen**: Revert the local path in `stream()` to the original implementation from before the change — yield each chunk as `run_in_executor` produces it. The queue was added to prevent concurrent local LLM invocations, but streaming should still yield progressively, not buffer.

Solution: Don't route `stream()` through the queue for the actual content production. Instead, have the queue gate the start of streaming (ensuring serialization), but once streaming begins, yield chunks directly. This means the queue's `submit()` returns a generator/iterator, not a string.

**Alternatives considered**:
- `asyncio.Queue` for chunk forwarding: Overly complex for what's needed.
- Skip queue for streaming: Would allow concurrent streaming calls, breaking serialization.

**Chosen approach**: Change `LLMRequestQueue.submit()` to return the coroutine result directly (it already does). In `complete()`, this works as-is. In `stream()`, use the queue to serialize access to the LLM, then yield chunks from the internal queue directly back to the caller — not through the `LLMRequestQueue`.

Actually, the simplest fix: In `stream()`, keep the queue gate but return the generator. Change `_stream_all` to be an async generator that yields chunks, and have `stream()` iterate over it AFTER the queue gate. The queue only gates access — it doesn't need to collect results.

Simplest fix: Skip queue for `stream()`. Use `asyncio.Lock` instead to serialize access to the local LLM. The lock is simpler than the queue for streaming because the queue forces collecting all results before returning.

### 4. QueryResponse + thread_id

**Chosen**: Add `thread_id: Optional[str] = None` to the `QueryResponse` Pydantic model. This is a backward-compatible change — existing clients ignore the new field.

### 5. `validate_api_key` dead code

**Chosen**: Remove lines 48-50 (`stored_hash = ...; if not compare_digest(...); return None`). The hash lookup already validates the key. The `compare_digest` on identical inputs is a no-op.

### 6. `deactivate_api_key` reliability

**Chosen**: Change the SQL to `UPDATE api_keys SET is_active = FALSE WHERE id = %s RETURNING id` and check if the `RETURNING` clause produces a row. This is deterministic.

### 7. `/health` endpoint

**Chosen**: Add a simple `@app.get("/health")` route in `main.py` returning `{"status": "healthy"}`.

### 8. Rate limit path matching

**Chosen**: Replace `"/query" in path` with explicit prefix checks:
```python
def _is_query_path(path: str) -> bool:
    return path in ("/api/v1/query",) or path.startswith("/api/v1/query/") or path == "/ui/query/chat"
```

### 9. Conditional thread_id generation

**Chosen**: Only generate a `thread_id` when the caller explicitly provides one (even if empty). If no `thread_id` is provided at all, skip conversation storage entirely. The `else: thread_id = create_thread_id()` block is removed.

### 10. `Request = None` cleanup

**Chosen**: Change `request: Request = None` to `request: Request` in all endpoint signatures. FastAPI always injects `Request`.

### 11. Admin key fix

**Chosen**: When both `X-Admin-Key` and `X-API-Key` are present, treat the admin key as granting admin access but let the API key determine `tenant_id`. Admin-only key (without API key) still gets `tenant_id = "admin"`.

### 12. Async migration call

**Chosen**: Wrap `run_migrations()` in `await asyncio.to_thread(run_migrations)` in the lifespan. `run_migrations` uses sync connections (fine for setup), but shouldn't block the event loop.

## Risks / Trade-offs

- **Stream fix using `asyncio.Lock`**: If a streaming request hangs (LLM generates indefinitely), the lock is never released, blocking all subsequent local LLM requests. Mitigation: The lock is released when the streaming coroutine exits (including cancellation). Add a timeout wrapper on the generator.
- **Removing auto thread_id**: Existing clients that relied on always getting a `thread_id` in the response will now see `None` when they don't send one. This is a behavioral change but matches the spec (conversation memory should be opt-in).
- **`Literal` import adds a dependency on psycopg API surface**: `psycopg.sql.Literal` is stable and has been available since psycopg 3.0. It's already installed.
