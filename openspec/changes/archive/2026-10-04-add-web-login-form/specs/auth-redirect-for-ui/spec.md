## ADDED Requirements

### Requirement: AuthMiddleware redirects HTML requests to login
When authentication is enabled and no valid API key is present, the `AuthMiddleware` SHALL redirect requests with `Accept: text/html` to `/login?next=<original_path>` instead of returning a JSON 401 response.

#### Scenario: Browser requests protected page without auth
- **WHEN** a request with `Accept: text/html` header hits a protected path without a valid API key
- **THEN** the middleware returns an HTTP 302 redirect to `/login?next=<original_path>`

#### Scenario: API client requests protected endpoint without auth
- **WHEN** a request without `Accept: text/html` header hits a protected path without a valid API key
- **THEN** the middleware returns an HTTP 401 JSON response with `{"error": "Missing API key"}`

#### Scenario: Login page is exempt from auth
- **WHEN** a request hits `/login` regardless of `Accept` header or API key presence
- **THEN** the middleware allows the request to pass through without authentication
