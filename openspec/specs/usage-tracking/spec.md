# Usage Tracking

## Purpose

Asynchronously log per-request usage data (tokens, chunks, operations) to a database table, with tenant-scoped aggregation via a dedicated API endpoint. Logging failures never block the API response.

## Requirements

### Requirement: Per-request usage logging
After every successful query, the system SHALL asynchronously log usage data to the `usage_logs` table: `tenant_id`, `operation` (query/ingest), `tokens_prompt`, `tokens_completion`, `chunks_retrieved`, `timestamp`. Logging SHALL NOT block the API response.

#### Scenario: Query usage logged
- **WHEN** Tenant A makes a query that consumes 500 prompt tokens and 200 completion tokens
- **THEN** a `usage_logs` row is inserted with `operation = 'query'`, `tokens_prompt = 500`, `tokens_completion = 200`

#### Scenario: Logging failure does not affect response
- **WHEN** the `usage_logs` insert fails (e.g., DB unavailable)
- **THEN** the query response is still returned successfully to the client

### Requirement: Ingestion usage logging
After every successful ingestion, the system SHALL log: `tenant_id`, `operation = 'ingest'`, `chunks_created`, `tokens_embedded`, `source_name`.

#### Scenario: File ingestion logged
- **WHEN** Tenant A ingests a PDF that creates 50 chunks
- **THEN** a `usage_logs` row is inserted with `operation = 'ingest'`, `chunks_created = 50`

### Requirement: Usage aggregation endpoint
The system SHALL provide `GET /api/v1/usage` that returns aggregated usage statistics for the requesting tenant: total queries, total tokens consumed, total chunks stored, over a configurable time range (default: last 30 days).

#### Scenario: Daily usage summary
- **WHEN** Tenant A requests `GET /api/v1/usage?days=7`
- **THEN** the response includes total queries, total prompt tokens, total completion tokens, and total ingests for the last 7 days

### Requirement: Tenant-scoped usage data
Usage data SHALL be scoped to the requesting tenant. One tenant SHALL NOT be able to view another tenant's usage statistics.

#### Scenario: Cross-tenant usage access denied
- **WHEN** Tenant A requests usage data
- **THEN** only rows with `tenant_id = 'tenant_a'` are included in the aggregation