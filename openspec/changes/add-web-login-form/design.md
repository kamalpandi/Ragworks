## Context

The system uses `AuthMiddleware` to validate API keys via `X-API-Key` header or `Authorization: Bearer`. This works for programmatic API consumers but blocks browser-based access to the HTMX web UI. Currently, the only workaround is `AUTH_ENABLED=False`. The web UI needs a login page where users paste their API key once, have it stored client-side, and have it automatically included in subsequent requests.

The existing `api_keys` table stores SHA-256 hashed keys by `tenant_id`. `validate_api_key()` compares the provided key hash and returns `(tenant_id, key_id)` on success. This function is already used by the middleware and can be reused for login validation.

## Goals / Non-Goals

**Goals:**
- Provide a `/login` page with a form to enter an API key
- Validate the key server-side and return the raw key + metadata to the client
- Store the key in `localStorage` and inject it via `X-API-Key` header on all browser requests
- Redirect browser requests to `/login` when auth fails (instead of JSON 401)
- Add a logout mechanism that clears stored credentials

**Non-Goals:**
- Creating API keys through the login page (use existing admin endpoints)
- Session-based auth or server-side cookies
- Username/password authentication
- OAuth or SSO integration
- Changing the API-level auth flow (X-API-Key / Bearer headers remain unchanged)

## Decisions

### Decision 1: Redirect HTML requests to `/login`, return JSON 401 for API requests

**Chosen**: In `AuthMiddleware.dispatch()`, when no valid API key is found, check `Accept` header. If it contains `text/html`, return a 302 redirect to `/login?next=<original_path>`. Otherwise, return the existing JSON 401.

**Alternative**: Always return 401 and handle redirect on the client side.
**Rationale**: Browser users expect a redirect to a login page. API consumers expect structured error responses. Using the `Accept` header follows HTTP conventions and requires no client-side redirect logic.

### Decision 2: Store raw API key in localStorage, not a JWT

**Chosen**: After successful login validation, return the raw API key to the client. Client stores it in `localStorage` under `rag_api_key`. All requests include it via `X-API-Key` header.

**Alternative**: Generate a JWT on login, store JWT, validate JWT in middleware.
**Rationale**: The existing `validate_api_key()` function already handles fast lookup. Introducing JWT would add token signing, expiration, and refresh complexity without benefit — since the underlying API key is already a secure random string. localStorage is acceptable because the key is already shown to the user (created via admin endpoint).

### Decision 3: Use HTMX `htmx:configRequest` event to inject the header

**Chosen**: A global JS listener on `htmx:configRequest` reads `localStorage.getItem("rag_api_key")` and sets `event.detail.headers["X-API-Key"]`. This covers all HTMX-driven form submissions and link follows.

**Alternative**: Use `hx-headers` attribute on every element.
**Rationale**: A single event listener is DRY — it covers all current and future HTMX interactions without modifying individual elements. Non-HTMX requests (e.g., page reloads) are handled by the login redirect flow.

### Decision 4: Login page as a separate UI route, not part of the API

**Chosen**: `GET /login` returns an HTML page. `POST /login` validates the key and returns JSON. The client handles the redirect after successful login.

**Rationale**: Clean separation — `/login` is a UI route, not an API endpoint. The POST returns JSON so the client can decide what to do next (navigate to `?next=` URL or `/`).

### Decision 5: Add logout UI in base template

**Chosen**: When an API key is present in localStorage, show a "Logout" link/button in the base template nav. On click, clear localStorage and redirect to `/login`.

**Rationale**: Users need a way to switch accounts or log out. Detecting login state via JS + localStorage keeps this purely client-side with no server-side session.

## Risks / Trade-offs

- **[Low] API key in localStorage**: If an XSS vulnerability exists, the API key could be stolen. Mitigation: The key is already a known value the user possesses (created by admin), not a derived secret. This is inherent to API-key-based auth. The risk is comparable to a user copy-pasting the key into curl.
- **[Low] Login page accessible without auth**: The `/login` path is exempt from auth, meaning anyone can reach it. Mitigation: The login form requires a valid API key to proceed — without one, the user cannot access any protected pages.
- **[Low] No session timeout or key rotation**: The key persists indefinitely in localStorage. Mitigation: This matches the current API key model where keys never expire. Future work could add key expiry without breaking this flow.
