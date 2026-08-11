## Context

The RAG framework is currently single-tenant: all vector data lives in one PGVector table, LLM instances are process singletons, and there is no authentication or rate limiting. The codebase uses FastAPI with async IO, Prometheus metrics, OTEL tracing, and interface-based components (LLM, VectorDB, Embedder, Reranker). The existing `BaseVectorDB`, `BaseLLM`, and `BaseEmbedder` interfaces provide clean extension points for tenant-aware wrappers without rewriting the core.

The user wants the system to work with both local (ollama, llamacpp) and cloud (OpenAI) LLM providers. This constrains the concurrency model: local models cannot serve concurrent requests, so a queuing mechanism is needed.

## Goals / Non-Goals

**Goals:**
- Isolate data per tenant so tenants cannot query each other's documents
- Authenticate every API request via API key or Bearer token
- Throttle requests per tenant to prevent noisy-neighbor issues
- Pool PGVector connections for concurrent throughput
- Queue local LLM requests to avoid concurrent invocation failures
- Store and inject conversation history for follow-up queries
- Track token usage and request counts per tenant

**Non-Goals:**
- Per-tenant LLM model selection (all tenants use the configured provider)
- Billing/invoicing system (just usage data storage)
- User management within tenants (single API key per tenant for v1)
- Redis dependency (rate limiting is in-memory; migratable later)
- Tenant self-service registration UI (API-only tenant creation)
- Streaming responses (separate roadmap item)

## Decisions

### 1. Tenant Isolation: Single-Table with `tenant_id` Column

**Chosen**: Add `tenant_id` column to existing vector tables (`rag_vectors_512`, etc.) and filter every query with `WHERE tenant_id = $1`.

**Alternatives considered**:
- *Per-tenant tables* (`rag_vectors_512_tenant_abc`): Better physical isolation but explodes table count, complicates HNSW index management, and requires dynamic SQL table creation.
- *Per-tenant PostgreSQL schemas*: Strong isolation but requires per-tenant connection strings or `SET search_path`, complicates connection pooling.

**Rationale**: Single-table with `tenant_id` is the pragmatic choice for PGVector. A composite index on `(tenant_id, embedding)` or just filtering by `tenant_id` before the vector distance sort keeps queries isolated. This survives a simple migration (add column, backfill).

### 2. Authentication: FastAPI Middleware with API Key Store

**Chosen**: Add a `AuthMiddleware` registered in `main.py` (before routes) that extracts the API key from `X-API-Key` header or `Authorization: Bearer <key>`, validates against a database-backed `api_keys` table, and injects `tenant_id` into `request.state`.

**Alternatives considered**:
- *FastAPI Depends() per-route*: More explicit but requires modifying every route handler — fragile, easy to miss new routes.
- *External API gateway (Kong, nginx)*: Production-grade but adds infrastructure dependency. Out of scope for local-first deployment.
- *JWT with refresh tokens*: Overkill for API-based RAG consumption. API keys are simpler and standard for service-to-service.

**Rationale**: Middleware catches all routes (REST + UI) in one place. `request.state` carries tenant context through to services without changing function signatures. This mirrors the existing `ObservabilityMiddleware` pattern already in the codebase.

### 3. Rate Limiting: Token Bucket per Tenant (In-Memory)

**Chosen**: In-memory token bucket algorithm keyed by `tenant_id`, resetting per time window. Limits are configurable: `RATE_LIMIT_QUERIES_PER_MINUTE`, `RATE_LIMIT_INGEST_PER_MINUTE`. A `RateLimitMiddleware` sits after auth (needs `tenant_id` from `request.state`).

**Alternatives considered**:
- *Redis-backed*: Survives restarts and works across workers. But requires a Redis instance — conflicts with the local-first (no external dependencies) philosophy.
- *Sliding window log*: More precise but more memory. Token bucket is simpler and sufficient.

**Rationale**: In-memory works for single-process deploys (the current model). The middleware is designed so swapping to Redis later is a drop-in replacement without changing the rate-limit interface. Limits reset on restart — acceptable for v1.

### 4. Connection Pooling: `psycopg_pool.AsyncConnectionPool`

**Chosen**: Replace `psycopg.AsyncConnection.connect(...)` with `psycopg_pool.AsyncConnectionPool`. A single pool is created at startup (in `lifespan`) and passed to `PGVectorDB` via the dependency injection layer.

**Alternatives considered**:
- *asyncpg pool*: Faster but different library. Would require rewriting all PGVector queries from `psycopg` SQL to `asyncpg` dialect — unnecessary churn.
- *SQLAlchemy async*: Adds an ORM layer the project doesn't currently use. More abstraction than needed.

**Rationale**: `psycopg_pool` shares the same connection library (`psycopg`), supports async, and requires minimal code changes. Added to `pyproject.toml` as a dependency.

### 5. LLM Concurrency: Async Queue with Single Worker

**Chosen**: For local LLM providers (`llamacpp`), wrap the `complete()` call with an `asyncio.Queue` that serializes access. Requests are pushed onto the queue and a single worker processes them sequentially. Configurable timeout (`LLM_QUEUE_TIMEOUT_SECONDS`) so requests don't hang indefinitely.

```
                    ┌────────────────────┐
Request A ─────────▶│  asyncio.Queue     │
Request B ─────────▶│  (maxsize=None)    │────▶ Worker (sequential)
Request C ─────────▶│                    │       LlamaCpp._llm.invoke()
                    └────────────────────┘
```

**Alternatives considered**:
- *Load multiple model instances*: Memory-prohibitive for 8B+ parameter models.
- *External llama.cpp server with `-np` flag*: Would solve it but adds deployment complexity.
- *Reject concurrent requests with 503*: Simpler but poor UX.

**Rationale**: OpenAI and Ollama use stateless HTTP clients — no queuing needed. The queue is gated behind a provider check: only activated for `llamacpp`. The existing `@lru_cache` singleton model loading is preserved.

### 6. Conversation Memory: DB-Backed Threads

**Chosen**: Store conversations in a `conversations` table with columns: `id`, `tenant_id`, `thread_id`, `role` (user/assistant), `content`, `created_at`. On query, retrieve the last N messages for the thread, format them into the LLM prompt as chat history. A new optional `thread_id` field is added to `ChatRequest`.

**Alternatives considered**:
- *Client-side storage* (cookies/localStorage): Stateless server but loses history across devices and can't be used by API consumers.
- *LangChain memory*: Adds a heavy dependency for a simple key-value store.

**Rationale**: Simple SQL table, no vector search needed. Chat history is injected into the prompt between system prompt and retrieved context. Default window: last 10 messages. Threads are identified by UUID, created on first query if no `thread_id` provided.

### 7. Usage Tracking: Async Fire-and-Forget Logging

**Chosen**: After each query and ingest operation, fire an async background task that inserts a row into `usage_logs`: `tenant_id`, `operation` (query/ingest), `tokens_prompt`, `tokens_completion`, `timestamp`, `chunks_retrieved`. No await — the response doesn't wait for logging.

**Alternatives considered**:
- *Synchronous logging*: Adds latency to every request.
- *Separate analytics service*: Over-engineering for v1.

**Rationale**: Usage logs are eventually consistent. Dropping a log row is acceptable for now. The table structure supports aggregation queries for dashboards later.

## Risks / Trade-offs

- **In-memory rate limiting resets on restart** → Accept for v1. Document that Redis swap is straightforward. The `RateLimiter` interface is abstract.
- **Single-table tenancy means a bug in the WHERE clause leaks data** → Mitigated by integration tests that verify cross-tenant isolation. Every query path MUST include `tenant_id`.
- **Local LLM queue can grow unbounded under sustained load** → Default `LLM_QUEUE_TIMEOUT_SECONDS=120`. Requests time out and return 503 after the timeout. Monitor queue depth via existing Prometheus metrics.
- **API key store in same DB as vector data** → Acceptable for now. Keys are plaintext (hashed in v2). If the DB is compromised, vectors are also compromised — same threat model.
- **`tenant_id` column migration on existing data** → All existing rows need a default tenant (e.g., `"default"`). Migration script adds the column with a default, then removes the default constraint after backfill.
- **`conversations` table growth** → Add a TTL or retention policy later. For v1, conversations are append-only. Add an index on `(tenant_id, thread_id, created_at)`.
