## ADDED Requirements

### Requirement: API key stored in localStorage after login
After a successful login, the client-side JavaScript SHALL store the validated API key in `localStorage` under the key `rag_api_key`.

#### Scenario: Successful login stores key
- **WHEN** the login endpoint returns a successful JSON response with an `api_key` field
- **THEN** the client stores `api_key` in `localStorage` under `rag_api_key`

### Requirement: API key injected into all HTMX requests
The client-side JavaScript SHALL listen for the `htmx:configRequest` event and inject the stored API key as an `X-API-Key` header on every HTMX request.

#### Scenario: HTMX request includes API key
- **WHEN** HTMX initiates a request and `localStorage` contains `rag_api_key`
- **THEN** the request includes an `X-API-Key` header with the stored key value

#### Scenario: HTMX request without stored key
- **WHEN** HTMX initiates a request and `localStorage` does NOT contain `rag_api_key`
- **THEN** the request does NOT include an `X-API-Key` header

### Requirement: Logout clears stored key and redirects
The client-side JavaScript SHALL provide a logout function that removes the API key from `localStorage` and redirects the browser to `/login`.

#### Scenario: User logs out
- **WHEN** a user clicks the logout button
- **THEN** `rag_api_key` is removed from `localStorage` and the browser navigates to `/login`
