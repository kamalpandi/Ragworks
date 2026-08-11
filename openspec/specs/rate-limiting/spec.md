# Rate Limiting

## Purpose

Enforce per-tenant request rate limits for query and ingest endpoints, with configurable windows and independent tenant isolation. Rate-limited responses include retry-after headers.

## Requirements

### Requirement: Per-tenant query rate limiting
The system SHALL enforce a configurable maximum number of query requests per tenant per time window. Requests exceeding the limit SHALL receive HTTP 429.

#### Scenario: Tenant within limit
- **WHEN** Tenant A makes 5 queries in one minute and the limit is 60 queries/minute
- **THEN** all 5 requests succeed with HTTP 200

#### Scenario: Tenant exceeds limit
- **WHEN** Tenant A exceeds the configured rate limit for queries
- **THEN** subsequent requests within the same window return HTTP 429 with `{"error": "Rate limit exceeded", "retry_after_seconds": <seconds>}`

#### Scenario: Rate limit response includes retry-after
- **WHEN** a rate-limited response is returned
- **THEN** the response includes a `Retry-After` header with the remaining seconds in the current window

### Requirement: Per-tenant ingest rate limiting
The system SHALL enforce a separate, configurable rate limit for ingestion endpoints (`/api/v1/ingest/*`).

#### Scenario: High ingest volume throttled
- **WHEN** Tenant A triggers 20 file ingestions in one minute and the ingest limit is 10/minute
- **THEN** the 11th through 20th requests return HTTP 429

### Requirement: Rate limits are tenant-isolated
Tenant A's rate limit consumption SHALL NOT affect Tenant B's allowance.

#### Scenario: Independent tenant limits
- **WHEN** Tenant A exhausts their query limit
- **THEN** Tenant B can still make queries up to their own limit

### Requirement: Configurable rate limit windows
Rate limit parameters SHALL be configurable via environment variables: `RATE_LIMIT_QUERIES_PER_MINUTE`, `RATE_LIMIT_INGEST_PER_MINUTE`, `RATE_LIMIT_BURST_SIZE`.

#### Scenario: Default configuration
- **WHEN** no rate limit env vars are set
- **THEN** the system uses built-in defaults (e.g., 60 queries/min, 10 ingests/min)