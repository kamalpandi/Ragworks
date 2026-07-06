## Why

The framework currently operates as a single-tenant RAG tool — all users share one database table, one LLM instance, no authentication, and no tenant isolation. External applications cannot safely coexist. To serve as a production-ready RAG-as-a-Service platform, the system needs multi-tenancy, authentication, rate limiting, connection pooling, per-user conversation memory, and usage tracking. This is the foundational change that makes every subsequent feature (streaming, hybrid search, Qdrant) usable by multiple tenants simultaneously.

## What Changes

- **Multi-tenancy**: Introduce tenant IDs on all data paths — every ingested document, vector chunk, and query is scoped to a tenant. Queries without a valid tenant are rejected. **BREAKING**: existing `file_name`-based query filtering is replaced by tenant-scoped filtering.
- **API Key Authentication**: All API endpoints require a valid API key passed via `X-API-Key` header or `Authorization: Bearer` token. Unauthenticated requests return 401. Keys are managed via a new API key store.
- **Rate Limiting**: Per-tenant request throttling on query and ingest endpoints, configurable limits with burst tolerance. Rate-limited requests return 429.
- **Database Connection Pooling**: Replace per-operation connection creation in `PGVectorDB` with a pooled connection manager, improving throughput under concurrent load.
- **LLM Concurrency**: Add a request queue with configurable timeout for local LLM providers (llama.cpp). OpenAI and Ollama remain stateless and need no queuing.
- **Conversation Memory**: Store per-user, per-tenant conversation threads so follow-up questions have context. Previous Q&A pairs are included in the LLM prompt.
- **Usage Tracking**: Log token consumption, request counts, and storage usage per tenant for billing/observability.
- **Configuration Endpoint Hardening**: The `/api/v1/config` endpoint returns only tenant-scoped configuration. Non-sensitive settings are gated behind authentication.

## Capabilities

### New Capabilities

- `multi-tenancy`: Tenant-scoped data isolation for ingestion, vector storage, and query retrieval. Every API operation carries a tenant context.
- `api-authentication`: API key and Bearer token authentication middleware for all `/api/v1/*` and `/ui/*` endpoints.
- `rate-limiting`: Configurable per-tenant rate limiting with burst tolerance, returning HTTP 429 when exceeded.
- `connection-pooling`: Shared database connection pool for PGVector operations, replacing per-op connection creation.
- `llm-concurrency`: Request queue with timeout for local LLM providers (llama.cpp), preventing concurrent invocation failures.
- `conversation-memory`: Per-user conversation thread storage enabling follow-up queries with full context.
- `usage-tracking`: Per-tenant metrics for token consumption, request counts, and storage operations.

### Modified Capabilities

- _(none — no existing specs to modify. This is the first formal capability spec.)_

## Impact

- **Affected code**:
  - `app/core/dependencies.py` — tenant context injection
  - `app/core/config.py` — new auth, rate-limit, pooling settings
  - `app/api/v1/endpoints/*` — authentication dependency on all routes
  - `app/ui/*` — authentication on all UI routes
  - `app/components/vector_dbs/pgvector_db.py` — connection pooling, tenant-scoped queries
  - `app/components/vector_dbs/pinecone_db.py` — tenant-scoped namespaces
  - `app/services/rag_engine.py` — conversation memory, usage tracking
  - `app/services/ingestion.py` — tenant-scoped ingestion
  - `app/models/api_requests.py` — optional tenant/API key fields
  - `app/models/domain.py` — new conversation models
  - `app/api/v1/api.py` — auth middleware registration
  - `main.py` — middleware stack changes
- **New files**:
  - `app/middleware/auth.py` — authentication middleware
  - `app/middleware/rate_limit.py` — rate limiting middleware
  - `app/middleware/tenant.py` — tenant context middleware
  - `app/services/tenant_manager.py` — tenant lifecycle management
  - `app/models/conversation.py` — conversation data models
  - `app/core/pool.py` — connection pool manager
  - `app/services/usage_tracker.py` — usage metrics service
- **Dependencies**: `asyncpg` or `psycopg_pool` for connection pooling, `pyjwt` or `itsdangerous` for API key management
- **Database**: New tables: `api_keys`, `tenants`, `conversations`, `usage_logs`. Modified: vector tables gain `tenant_id` column.
