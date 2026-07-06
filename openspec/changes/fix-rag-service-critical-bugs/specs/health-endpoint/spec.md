## ADDED Requirements

### Requirement: Health check endpoint
The system SHALL expose a `GET /health` endpoint that returns HTTP 200 with `{"status": "healthy"}` when the application is running.

#### Scenario: Health check succeeds
- **WHEN** a GET request is made to `/health`
- **THEN** the system returns HTTP 200 with body `{"status": "healthy"}`

#### Scenario: Health check is exempt from authentication
- **WHEN** a GET request is made to `/health` without an API key
- **THEN** the system returns HTTP 200 (not 401)
