## Purpose

Enforce a strict separation of concerns in which the backend serves JSON only and owns all data and logic, while the frontend renders HTML only and reaches the backend exclusively over HTTP.

## ADDED Requirements

### Requirement: Backend serves JSON only
All backend API endpoints under `/api/v1/*` SHALL return machine-readable JSON (or documented non-HTML content types) and SHALL NOT render HTML templates, emit HTML fragments, or vary response format based on the `HX-Request` header.

#### Scenario: API request receives JSON
- **WHEN** a client sends `GET /api/v1/eval/results` with `HX-Request: true`
- **THEN** the response body is JSON, not an HTML fragment

#### Scenario: No HTML content negotiation
- **WHEN** any `/api/v1/*` endpoint is invoked with or without `HX-Request`
- **THEN** the response content type and body are identical

### Requirement: Frontend is render-only
The frontend SHALL NOT access the database, vector store, LLM providers, filesystem prompt or evaluation stores, or backend service modules directly. It SHALL obtain all data by calling the backend HTTP API.

#### Scenario: Fragment data obtained over HTTP
- **WHEN** a frontend fragment route needs data to render
- **THEN** it retrieves that data through the backend HTTP API rather than through a direct service or database call

#### Scenario: No backend internals imported
- **WHEN** the frontend source is inspected
- **THEN** it imports no backend service, pool, component, model, evaluation, observability, or middleware module

### Requirement: Enforced import contract
An automated architecture check SHALL fail if `app/frontend/*` imports any backend module other than shared configuration, or if any backend module imports `app.frontend`, `jinja2`, or `starlette.templating`.

#### Scenario: Frontend violation detected
- **WHEN** a frontend module imports a backend service or database pool
- **THEN** the architecture check reports a failure

#### Scenario: Backend violation detected
- **WHEN** a backend module imports `jinja2` or `app.frontend`
- **THEN** the architecture check reports a failure

#### Scenario: Clean tree passes
- **WHEN** the import contract is respected
- **THEN** the architecture check passes

### Requirement: Browser reaches only the frontend
The browser SHALL issue requests only to frontend routes. All requests to the backend API SHALL originate server-side from the frontend.

#### Scenario: No direct browser API access
- **WHEN** a user interacts with any page or fragment in the browser
- **THEN** the browser's network requests target frontend routes and never `/api/v1/*` directly
