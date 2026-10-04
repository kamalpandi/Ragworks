# dashboard-api Specification

## Purpose
Expose system status and a single aggregate dashboard view model as JSON so the UI can render the dashboard without orchestrating multiple backend calls.

## Requirements

### Requirement: System status endpoint
The backend SHALL expose `GET /api/v1/status` returning a JSON object describing system status, including database connectivity.

#### Scenario: Status returned as JSON
- **WHEN** an authenticated client requests `GET /api/v1/status`
- **THEN** the response is JSON containing at least the database connectivity status

#### Scenario: Status requires authentication
- **WHEN** a client requests `GET /api/v1/status` without a valid API key
- **THEN** the backend responds with HTTP 401

### Requirement: Aggregate dashboard endpoint
The backend SHALL expose `GET /api/v1/dashboard` returning a single JSON view model containing system status, usage statistics, recent activity, and ingested documents for the requesting tenant.

#### Scenario: Aggregate view model returned
- **WHEN** an authenticated client requests `GET /api/v1/dashboard`
- **THEN** the response JSON includes status, usage statistics, recent activity, and ingested documents in one payload

#### Scenario: Dashboard is tenant scoped
- **WHEN** a tenant requests `GET /api/v1/dashboard`
- **THEN** the returned statistics, activity, and documents include only data belonging to that tenant

#### Scenario: Dashboard requires authentication
- **WHEN** a client requests `GET /api/v1/dashboard` without a valid API key
- **THEN** the backend responds with HTTP 401
