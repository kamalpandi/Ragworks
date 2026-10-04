## MODIFIED Requirements

### Requirement: API key validation middleware
Every request to `/api/v1/*` SHALL be intercepted by authentication middleware that extracts and validates an API key before the request reaches route handlers. Browser-facing frontend routes SHALL NOT be validated by this middleware; they are authenticated by the frontend session layer instead.

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

#### Scenario: Frontend route not API-key authenticated
- **WHEN** a browser requests `/query` with a valid session cookie but no API key header
- **THEN** the API key middleware does not reject the request

## REMOVED Requirements

### Requirement: Exempt endpoints

## ADDED Requirements

### Requirement: Middleware scope
The API-key authentication middleware SHALL apply only to requests under `/api/v1/*`. Requests outside that prefix — including `/metrics`, `/docs`, `/openapi.json`, `/health`, and `/login`, and all browser-facing pages and fragments — SHALL NOT be validated by the API-key middleware. Browser-facing pages and fragments SHALL instead require a valid frontend session, and unauthenticated browser requests to them SHALL be redirected to `/login`.

#### Scenario: Access metrics without API key
- **WHEN** a GET request is made to `/metrics` without an API key
- **THEN** the system returns Prometheus metrics (200 OK)

#### Scenario: Access dashboard without session
- **WHEN** a browser GET request is made to `/` without a valid session cookie or API key
- **THEN** the system responds with HTTP 302 redirecting to `/login`

### Requirement: API key identity endpoint
The backend SHALL expose `GET /api/v1/auth/me` that returns the tenant identifier and key identifier associated with the presented API key, and SHALL return HTTP 401 for a missing or invalid key.

#### Scenario: Valid key returns identity
- **WHEN** an authenticated client requests `GET /api/v1/auth/me` with a valid API key
- **THEN** the backend responds with HTTP 200 and JSON containing `tenant_id` and `key_id`

#### Scenario: Invalid key returns 401
- **WHEN** a client requests `GET /api/v1/auth/me` with an invalid API key
- **THEN** the backend responds with HTTP 401 and a JSON error body
