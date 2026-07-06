## ADDED Requirements

### Requirement: Login page renders
The system SHALL serve a login page at `GET /login` with an HTML form containing an API key input field and a submit button.

#### Scenario: User navigates to login page
- **WHEN** a user visits `/login` in a browser
- **THEN** the system returns an HTML page with a form containing an API key text input and a "Login" submit button

#### Scenario: Login page includes redirect parameter
- **WHEN** a user is redirected to `/login?next=/query`
- **THEN** the login form includes a hidden `next` field preserving the original destination path

### Requirement: Login validates API key
The system SHALL provide a `POST /login` endpoint that accepts an API key, validates it against the `api_keys` table, and returns the key with tenant metadata on success.

#### Scenario: Valid API key submitted
- **WHEN** a user submits a valid API key via the login form
- **THEN** the system returns a JSON response with `{"success": true, "api_key": "<key>", "tenant_id": "...", "label": "..."}` and HTTP 200

#### Scenario: Invalid API key submitted
- **WHEN** a user submits an invalid or deactivated API key via the login form
- **THEN** the system returns a JSON response with `{"success": false, "error": "Invalid API key"}` and HTTP 401

#### Scenario: Empty API key submitted
- **WHEN** a user submits an empty API key via the login form
- **THEN** the system returns a JSON response with `{"success": false, "error": "API key is required"}` and HTTP 400
