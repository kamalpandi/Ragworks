## 1. AuthMiddleware Redirect for HTML Requests

- [x] 1.1 Add redirect logic in `app/middleware/auth.py:31-41`: when no API key and `Accept` header contains `text/html`, return `RedirectResponse("/login?next=<path>")` instead of JSON 401
- [x] 1.2 Import `RedirectResponse` from `starlette.responses` in `app/middleware/auth.py`
- [x] 1.3 Add `/login` to the default `AUTH_EXEMPT_PATHS` in `app/core/config.py`

## 2. Login Page and Endpoint

- [x] 2.1 Create `app/ui/login.py` with `GET /login` route that renders a login page template
- [x] 2.2 Create `app/templates/pages/login.html` with an API key input form, hidden `next` field from query param, and JavaScript to handle the login flow
- [x] 2.3 Add `POST /login` endpoint in `app/ui/login.py` that validates the API key via `validate_api_key()` and returns JSON `{"success": true, "api_key": "...", "tenant_id": "...", "label": "..."}`
- [x] 2.4 Register the login router in `app/ui/router.py`
- [x] 2.5 Ensure the login template has no nav links (standalone page) and uses Pico CSS styling consistent with the rest of the UI

## 3. Client-Side Token Management

- [x] 3.1 Add a `<script>` block or static JS file that listens for `htmx:configRequest` and injects `X-API-Key` from `localStorage.getItem("rag_api_key")`
- [x] 3.2 Add login form submission JS: on form submit, POST to `/login`, on success store `api_key` in localStorage and redirect to `next` param or `/`
- [x] 3.3 Add logout JS function that clears `localStorage.removeItem("rag_api_key")` and redirects to `/login`
- [x] 3.4 Include the JS in `app/templates/base.html` so it's available on all pages

## 4. Base Template Updates

- [x] 4.1 Add a logout button/link to the nav in `app/templates/base.html`, conditionally shown when `localStorage` has `rag_api_key`, that triggers the logout function
- [x] 4.2 Add the `htmx:configRequest` event listener as a `<script>` block in `base.html` (or ensure the JS from step 3 covers it)

## 5. Linting & Verification

- [x] 5.1 Run `ruff check . && ruff format .` to verify no lint errors
- [ ] 5.2 Start the app, visit `/` without auth → verify redirect to `/login?next=/`
- [ ] 5.3 Submit a valid API key on the login form → verify redirect to destination and subsequent pages load
- [ ] 5.4 Submit an invalid API key → verify error message is shown
- [ ] 5.5 Click logout → verify redirect to `/login` and pages return to redirecting
- [ ] 5.6 Verify API clients (no `Accept: text/html`) still get JSON 401 as before
