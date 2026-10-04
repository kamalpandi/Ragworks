# web-session-auth Specification

## Purpose
Authenticate browser users with server-side sessions so the backend API key is never exposed to the browser, while state-changing requests are protected against cross-site request forgery.

## Requirements

### Requirement: Login with API key
The frontend SHALL validate a submitted API key against the backend identity endpoint and, on success, create a server-side session and set a session cookie. On failure it SHALL reject the login and create no session.

#### Scenario: Valid API key creates a session
- **WHEN** a user submits a valid API key to `POST /login`
- **THEN** the frontend creates a server-side session, sets an `HttpOnly` session cookie, and redirects the user to the requested page

#### Scenario: Invalid API key rejected
- **WHEN** a user submits an invalid API key to `POST /login`
- **THEN** the frontend creates no session and renders an authentication error

#### Scenario: Development key accepted
- **WHEN** a user submits the configured development API key
- **THEN** a session is created with the development tenant

### Requirement: Server-side session storage
The frontend SHALL store session data server-side, keyed by an opaque session identifier. The session cookie SHALL contain only the opaque identifier and SHALL NOT contain the API key. Sessions SHALL expire after a configured time-to-live.

#### Scenario: Cookie excludes the API key
- **WHEN** a session cookie is issued
- **THEN** the cookie value is an opaque identifier and contains no API key material

#### Scenario: Expired session requires re-authentication
- **WHEN** a request presents a session whose time-to-live has elapsed
- **THEN** the frontend treats the request as unauthenticated and redirects to login

### Requirement: CSRF protection
State-changing authenticated frontend requests (POST, PUT, DELETE) SHALL require a valid per-session CSRF token. Requests lacking a valid token SHALL be rejected. Because `POST /login` occurs before a session exists, the login page SHALL issue a short-lived pre-session CSRF token that the login submission SHALL present.

#### Scenario: Missing or invalid token rejected
- **WHEN** an authenticated state-changing request is submitted without a valid CSRF token
- **THEN** the frontend rejects the request with HTTP 403 and performs no state change

#### Scenario: Valid token accepted
- **WHEN** an authenticated state-changing request includes the session's valid CSRF token
- **THEN** the frontend processes the request

#### Scenario: Login without pre-session token rejected
- **WHEN** an unauthenticated user submits `POST /login` without the pre-session CSRF token
- **THEN** the frontend responds with HTTP 403 and creates no session

#### Scenario: Login with valid pre-session token accepted
- **WHEN** an unauthenticated user submits `POST /login` with a valid pre-session CSRF token
- **THEN** the frontend validates the API key and may create a session

### Requirement: Logout via POST
Logout SHALL be performed with `POST /logout` including a valid CSRF token, which invalidates the server-side session and clears the session cookie. A `GET /logout` SHALL NOT be supported.

#### Scenario: Logout invalidates session
- **WHEN** an authenticated user submits `POST /logout` with a valid CSRF token
- **THEN** the server-side session is deleted, the cookie is cleared, and the user is redirected to login

#### Scenario: GET logout not supported
- **WHEN** a GET request is made to `/logout`
- **THEN** the frontend responds with HTTP 405 and the session remains valid

### Requirement: Protected frontend routes
Frontend pages and fragment routes requiring authentication SHALL redirect unauthenticated browser requests to the login page.

#### Scenario: Unauthenticated page request redirects
- **WHEN** an unauthenticated browser requests `/query`
- **THEN** the frontend responds with HTTP 302 redirecting to `/login`
