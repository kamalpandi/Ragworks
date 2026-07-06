## ADDED Requirements

### Requirement: API key validation middleware
Every request to `/api/v1/*` and `/ui/*` SHALL be intercepted by authentication middleware that extracts and validates an API key before the request reaches route handlers.

#### Scenario: Valid API key in X-API-Key header
- **WHEN** a request includes `X-API-Key: valid-key-123`
- **THEN** the middleware sets `request.state.tenant_id` and `request.state.api_key_id`, and the request proceeds

#### Scenario: Valid Bearer token
- **WHEN** a request includes `Authorization: Bearer valid-key-456`
- **THEN** the middleware validates it identically to `X-API-Key` and proceeds

#### Scenario: Missing API key
- **WHEN** a request to `/api/v1/query` has no `X-API-Key` header and no `Authorization` header
- **THEN** the system returns HTTP 401 with `{"error": "Missing API key"}`

#### Scenario: Invalid API key
- **WHEN** a request includes `X-API-Key: invalid-key`
- **THEN** the system returns HTTP 401 with `{"error": "Invalid API key"}`

### Requirement: Exempt endpoints
The `/metrics`, `/docs`, `/openapi.json`, and `/health` endpoints SHALL be exempt from authentication. The `/` (dashboard) page SHALL require authentication.

#### Scenario: Access metrics without API key
- **WHEN** a GET request is made to `/metrics` without an API key
- **THEN** the system returns Prometheus metrics (200 OK)

#### Scenario: Access dashboard without API key
- **WHEN** a GET request is made to `/` without an API key
- **THEN** the system returns HTTP 401

### Requirement: API key storage
API keys SHALL be stored in a database table `api_keys` with columns: `id`, `key_hash`, `tenant_id`, `label`, `created_at`, `is_active`. Keys SHALL be validated via secure comparison.

#### Scenario: API key creation
- **WHEN** an admin creates a new API key for Tenant A
- **THEN** a row is inserted in `api_keys` with `tenant_id = 'tenant_a'` and the raw key is returned once (not stored in plaintext)

#### Scenario: Deactivated key
- **WHEN** a request uses an API key where `is_active = false`
- **THEN** the system returns HTTP 401 with `{"error": "API key deactivated"}`
