## 1. Database & Connection Pooling Foundation

- [x] 1.1 Add `psycopg_pool` to `pyproject.toml` dependencies
- [x] 1.2 Create `app/core/pool.py` with `ConnectionPoolManager` — initializes `AsyncConnectionPool` at startup, provides `get_pool()`, closes at shutdown
- [x] 1.3 Add pool config env vars to `app/core/config.py`: `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_TIMEOUT`
- [x] 1.4 Update `main.py` lifespan to initialize and close the connection pool
- [x] 1.5 Refactor `app/components/vector_dbs/pgvector_db.py`: replace `_get_async_connection()` with pool checkout (`await pool.connection()`), keep `_init_db()` using sync connection
- [x] 1.6 Add `tenant_id` column migration: alter `rag_vectors_{dim}` table to add `TEXT DEFAULT 'default'` column, then remove default constraint
- [x] 1.7 Create `api_keys` table migration: `id UUID PRIMARY KEY`, `key_hash TEXT UNIQUE NOT NULL`, `tenant_id TEXT NOT NULL`, `label TEXT`, `created_at TIMESTAMPTZ DEFAULT NOW()`, `is_active BOOLEAN DEFAULT TRUE`
- [x] 1.8 Create `conversations` table migration: `id UUID PRIMARY KEY`, `tenant_id TEXT NOT NULL`, `thread_id TEXT NOT NULL`, `role TEXT NOT NULL`, `content TEXT NOT NULL`, `created_at TIMESTAMPTZ DEFAULT NOW()`, with index on `(tenant_id, thread_id, created_at)`
- [x] 1.9 Create `usage_logs` table migration: `id UUID PRIMARY KEY`, `tenant_id TEXT NOT NULL`, `operation TEXT NOT NULL`, `tokens_prompt INT DEFAULT 0`, `tokens_completion INT DEFAULT 0`, `chunks_created INT DEFAULT 0`, `chunks_retrieved INT DEFAULT 0`, `source_name TEXT`, `created_at TIMESTAMPTZ DEFAULT NOW()`

## 2. Multi-Tenancy Data Layer

- [x] 2.1 Update `BaseVectorDB` interface: add `tenant_id` parameter to `upsert()`, `search()`, and `get_distinct_sources()`
- [x] 2.2 Update `PGVectorDB.upsert()`: include `tenant_id` in all INSERT statements and chunk metadata
- [x] 2.3 Update `PGVectorDB.search()`: add `WHERE tenant_id = %s` to all vector queries, preserve source filter
- [x] 2.4 Update `PGVectorDB.get_distinct_sources()`: add `WHERE metadata->>'tenant_id' = %s` filter
- [x] 2.5 Update `PineconeDB` to use tenant-scoped namespaces (namespace = `tenant_id`)
- [x] 2.6 Update `IngestionService.ingest_texts()`: accept and propagate `tenant_id` to chunks and vector DB calls
- [x] 2.7 Update `RAGEngine.answer_question()`: accept and propagate `tenant_id` to embed+search and ingestion calls
- [x] 2.8 Update `dependencies.py`: `get_ingestion_service()` and `get_rag_engine()` accept optional `tenant_id`

## 3. Authentication

- [x] 3.1 Add auth config env vars to `app/core/config.py`: `AUTH_ENABLED` (default True), `AUTH_EXEMPT_PATHS` (comma-separated list: `/metrics,/docs,/openapi.json,/health`)
- [x] 3.2 Create `app/services/api_key_manager.py`: `create_api_key(tenant_id, label)` → returns raw key, stores hash in DB; `validate_api_key(key)` → returns `(tenant_id, key_id)` or `None`; uses `secrets.compare_digest` for timing-safe comparison
- [x] 3.3 Create `app/middleware/auth.py`: `AuthMiddleware` that reads `X-API-Key` or `Authorization: Bearer <key>`, validates via `api_key_manager`, sets `request.state.tenant_id` and `request.state.api_key_id`
- [x] 3.4 Register `AuthMiddleware` in `main.py` (before `ObservabilityMiddleware`), respect `AUTH_EXEMPT_PATHS`
- [x] 3.5 When `AUTH_ENABLED=False`, inject a default `tenant_id = 'default'` into `request.state` so existing single-tenant usage still works
- [x] 3.6 Add `AdminAPIKeyMiddleware` or helper: when `X-Admin-Key` matches `ADMIN_API_KEY` env var, set `request.state.is_admin = True` for key management endpoints
- [x] 3.7 Create `POST /api/v1/admin/api-keys` endpoint for creating new API keys (admin-only)
- [x] 3.8 Create `DELETE /api/v1/admin/api-keys/{key_id}` endpoint for deactivating API keys (admin-only)

## 4. Rate Limiting

- [x] 4.1 Add rate limit config env vars to `app/core/config.py`: `RATE_LIMIT_ENABLED` (default True), `RATE_LIMIT_QUERIES_PER_MINUTE` (default 60), `RATE_LIMIT_INGEST_PER_MINUTE` (default 10), `RATE_LIMIT_BURST_SIZE` (default 5)
- [x] 4.2 Create `app/middleware/rate_limit.py`: `RateLimitMiddleware` with in-memory token bucket keyed by `tenant_id`; separate buckets for query (`/api/v1/query`, `/ui/query/chat`) and ingest (`/api/v1/ingest/*`, `/ui/ingest/*`) paths
- [x] 4.3 When rate limit exceeded, return HTTP 429 with JSON body `{"error": "Rate limit exceeded", "retry_after_seconds": N}` and `Retry-After` header
- [x] 4.4 Register `RateLimitMiddleware` in `main.py` after `AuthMiddleware`
- [x] 4.5 Add `rag_rate_limit_exceeded_total` Prometheus counter metric, labeled by `tenant_id` and `operation`

## 5. LLM Concurrency (Local Providers)

- [x] 5.1 Add `LLM_QUEUE_TIMEOUT_SECONDS` to `app/core/config.py` (default 120)
- [x] 5.2 Create `app/services/llm_queue.py`: `LLMRequestQueue` class wrapping `asyncio.Queue` with a single worker, `submit(task)` method returns a Future with timeout
- [x] 5.3 Update `LlamaCppProvider.complete()`: route through `LLMRequestQueue` when running in local mode (not remote URL)
- [x] 5.4 Update `LlamaCppProvider.stream()`: route through `LLMRequestQueue` for local mode streaming
- [x] 5.5 Add `rag_llm_queue_depth` gauge and `rag_llm_queue_timeout_total` counter to observability metrics
- [x] 5.6 Do NOT modify `OpenAIProvider` or `OllamaProvider` — they remain stateless and concurrent

## 6. Conversation Memory

- [x] 6.1 Create `app/models/conversation.py`: `ConversationMessage` and `ConversationThread` Pydantic models
- [x] 6.2 Create `app/services/conversation_service.py`: `store_message(tenant_id, thread_id, role, content)`, `get_thread(tenant_id, thread_id, limit)`, `create_thread(tenant_id)` → thread_id
- [x] 6.3 Add `CONVERSATION_HISTORY_LENGTH` to `app/core/config.py` (default 10)
- [x] 6.4 Add optional `thread_id` field to `ChatRequest` Pydantic model
- [x] 6.5 Update `RAGEngine.answer_question()`: accept `thread_id`, retrieve conversation history before query, inject into prompt, store user + assistant messages after response
- [x] 6.6 Update both `app/api/v1/endpoints/query.py` and `app/ui/query.py`: pass `thread_id` from request to engine, return `thread_id` in response
- [x] 6.7 Create `GET /api/v1/conversations/{thread_id}` endpoint for retrieving thread history
- [x] 6.8 Create `GET /api/v1/conversations` endpoint for listing threads for the tenant

## 7. Usage Tracking

- [x] 7.1 Create `app/services/usage_tracker.py`: `track_query(tenant_id, tokens_prompt, tokens_completion, chunks_retrieved)`, `track_ingest(tenant_id, chunks_created, source_name)` — both fire-and-forget async DB inserts
- [x] 7.2 Update `RAGEngine.answer_question()`: after successful response, call `usage_tracker.track_query()` with token counts
- [x] 7.3 Update `IngestionService.ingest_texts()`: after successful upsert, call `usage_tracker.track_ingest()` with chunk count
- [x] 7.4 Create `GET /api/v1/usage` endpoint: query `usage_logs` aggregated by day for the requesting tenant, support `?days=N` query param
- [x] 7.5 Add `rag_usage_queries_total` and `rag_usage_tokens_total` Prometheus counters

## 8. Wiring & Integration

- [x] 8.1 Update all REST endpoint handlers (`app/api/v1/endpoints/*.py`) to read `tenant_id` from `request.state` and pass it to services
- [x] 8.2 Update all UI endpoint handlers (`app/ui/*.py`) to read `tenant_id` from `request.state` and pass it to services
- [x] 8.3 Update `app/core/dependencies.py`: `get_ingestion_service(request: Request)` and `get_rag_engine(request: Request)` read tenant from `request.state`
- [x] 8.4 Update CORS middleware in `main.py` to allow per-tenant origins (configurable via `CORS_ALLOWED_ORIGINS` env var, default `*` for local dev)
- [x] 8.5 Add `GET /api/v1/config` to include `tenant_id` in frontend config response (non-sensitive)

## 9. Testing & Verification

- [x] 9.1 Write integration test: Tenant A and Tenant B ingest different documents, verify cross-tenant query isolation
- [x] 9.2 Write integration test: valid API key access, invalid key returns 401, missing key returns 401, exempt paths accessible
- [x] 9.3 Write integration test: rate limit exceeded returns 429, respects `Retry-After`, tenant isolation of limits
- [x] 9.4 Write unit test: `LLMRequestQueue` serializes concurrent calls, respects timeout
- [x] 9.5 Write integration test: conversation thread stores and retrieves messages, cross-tenant thread isolation
- [x] 9.6 Write integration test: usage logs are created after query and ingest, `GET /api/v1/usage` returns correct aggregation

## 10. Cleanup & Documentation

- [x] 10.1 Add new env vars to `.env.example` or README configuration section
- [x] 10.2 Remove `file_name` mandatory requirement from `ChatRequest` — query isolation is now tenant-based, file filter is optional
- [x] 10.3 Update `app/ui/query.py` UI to include thread selector (list existing threads for tenant)
- [x] 10.4 Run `ruff check . && ruff format .` for linting
- [x] 10.5 Run full demo pipeline script to verify end-to-end flow with auth enabled
