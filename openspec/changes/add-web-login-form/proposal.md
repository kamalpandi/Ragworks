## Why

The web UI requires manual API key header injection to use — there's no login page. Users must either disable auth entirely (`AUTH_ENABLED=False`) or craft curl requests to create keys. A proper login form lets users paste an API key once, have it persist across browser sessions, and use the full HTMX web interface without touching headers. This completes the multi-tenant auth story for browser-based users while keeping the existing API key flow intact for programmatic consumers.

## What Changes

- Add a `/login` page with a form to enter an API key
- Add a `POST /login` endpoint that validates the API key against the `api_keys` table
- Add client-side JavaScript to store the API key in `localStorage` and inject it into all browser requests via `X-API-Key` header
- Update `AuthMiddleware` to redirect browser (`Accept: text/html`) requests to `/login` instead of returning a JSON 401
- Add `/login` to `AUTH_EXEMPT_PATHS` so the login page is accessible without auth
- Add a logout mechanism (clear localStorage, redirect to login)
- Add API key display to the login page showing current key info (tenant_id, label) after successful login

## Capabilities

### New Capabilities
- `web-login-form`: Login page (`GET /login`) with API key input form and `POST /login` validation endpoint
- `client-token-management`: JavaScript that persists the API key in localStorage and injects it via `X-API-Key` header on all browser requests
- `auth-redirect-for-ui`: AuthMiddleware redirects browser requests to `/login` instead of returning JSON 401

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- Affected code: `app/ui/login.py` (new), `app/templates/pages/login.html` (new), `app/templates/base.html` (add logout button), `app/middleware/auth.py` (add redirect logic), `app/ui/router.py` (register new route), `app/core/config.py` (add `/login` to default exempt paths)
- No new dependencies
- No breaking changes — API consumers using `X-API-Key`/`Bearer` headers are unaffected
- The `/login` path must be added to `AUTH_EXEMPT_PATHS` default
