## Why

An architectural audit of the `multi-user-rag-service` change revealed 3 critical bugs that prevent the system from running (LLM queue never started, migration SQL crash, streaming broken), 3 high-severity correctness issues (thread_id dropped from API responses, dead auth validation code, unreliable key deactivation), and 8 medium-severity quality issues. These must be fixed before the system can be deployed or tested.

## What Changes

- **Fix LLM Request Queue**: Call `queue.start()` after creation so the worker processes queued tasks instead of hanging indefinitely.
- **Fix Migration SQL**: Replace `Identifier` with `Literal` in the `tenant_id` column migration to avoid a PostgreSQL syntax error on startup.
- **Fix Streaming**: Restore chunk-by-chunk yielding in `LlamaCppProvider.stream()` local path instead of buffering and yielding once.
- **Fix QueryResponse model**: Add `thread_id` field so conversation thread IDs are returned to API clients.
- **Fix `validate_api_key`**: Remove the dead `_hash_key()` + `compare_digest` code — the hash lookup already validates the key.
- **Fix `deactivate_api_key`**: Use `RETURNING id` instead of `rowcount` for reliable success detection.
- **Add `/health` endpoint**: Register a health check route so the exempt path in auth middleware resolves.
- **Fix rate limit path matching**: Replace broad `"/query" in path` with precise endpoint matching to avoid false positives.
- **Fix thread_id generation**: Only create new thread IDs when explicitly requested; don't generate one for every query.
- **Fix `Request = None` defaults**: Remove misleading `= None` defaults on injected `Request` parameters across endpoints.
- **Fix admin key behavior**: Admin passing both `X-Admin-Key` and `X-API-Key` gets correct tenant context from the API key, not overridden to `"admin"`.
- **Fix synchronous migration call in lifespan**: Run `run_migrations()` in a thread executor to avoid blocking the event loop.

## Capabilities

### New Capabilities

- `health-endpoint`: A `GET /health` route returning `{"status": "healthy"}` so load balancers and auth exempt path resolve correctly.

### Modified Capabilities

- _(none — no existing spec requirements are changing. These are implementation bug fixes.)_

## Impact

- **Affected code**:
  - `app/components/llms/llamacpp_llm.py` — queue start, stream fix
  - `app/components/vector_dbs/pgvector_db.py` — Literal import, migration SQL fix
  - `app/models/api_response.py` — `thread_id` field on `QueryResponse`
  - `app/services/api_key_manager.py` — dead code removal, `RETURNING id`
  - `app/middleware/auth.py` — admin key logic fix
  - `app/middleware/rate_limit.py` — precise path matching
  - `app/services/rag_engine.py` — conditional thread_id creation
  - `app/api/v1/endpoints/ingest.py` — `Request = None` cleanup
  - `app/api/v1/endpoints/query.py` — `Request = None` cleanup
  - `app/ui/ingest.py` — `Request = None` cleanup
  - `main.py` — `/health` endpoint, async migration wrapping
- **No new dependencies required**.
