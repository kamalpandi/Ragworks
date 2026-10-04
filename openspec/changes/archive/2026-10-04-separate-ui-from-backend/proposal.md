## Why

The FastAPI app currently serves two overlapping surfaces from the same modules: a JSON API at `/api/v1` and a server-rendered HTMX UI at `/ui` and `/`. This creates a bidirectional gray area — UI handlers run backend logic (`app/ui/dashboard.py` raw SQL, `app/ui/ingest.py` PDF parsing, `app/ui/query.py` RAG orchestration, `app/ui/prompts.py` prompt file CRUD, `app/ui/eval_ui.py` eval file access) while the backend renders HTML (`app/api/v1/endpoints/eval.py` inline Jinja + `HX-Trigger` + `HX-Request` sniffing). Logic is duplicated across parallel route trees, and the browser holds the backend API key.

This change establishes a single enforced boundary: the backend is JSON-only and owns all data/logic/auth; the frontend is render-only and reaches the backend exclusively over HTTP via an in-process client, with the API key held server-side.

## What Changes

- Introduce `app/frontend/` (replaces `app/ui/`): pages, fragments, templates, static assets, an `api_client` (httpx `ASGITransport`), a server-side `SessionStore`, CSRF handling, and dependency helpers.
- Enforce an import contract: `app/frontend/*` may not import backend modules (except shared `app.core.config`); backend modules may not import `jinja2`, `starlette.templating`, or `app.frontend`. Add `tests/test_architecture.py` as a hard gate.
- **BREAKING** Backend becomes JSON-only: remove all `if HX-Request` branches and HTML rendering from `app/api/v1/endpoints/eval.py` (inline Jinja, `_render_result_card`, `HX-Trigger`), and delete `GET /api/v1/eval/results/{id}/card` HTML output.
- Add `GET /api/v1/auth/me` (header-authenticated; returns `{tenant_id, key_id}` or clean `401`) to validate a submitted key without adding an exempt path.
- **BREAKING** Browser no longer receives or sends the API key. Login posts to the frontend, which validates via `/api/v1/auth/me`, creates a server-side session, and sets an `HttpOnly` `SameSite=Lax` cookie. Logout becomes `POST /logout` with a CSRF token (no `GET /logout`). Delete the `htmx:configRequest` key-injection and all browser key storage.
- Add per-session CSRF tokens: stored in `SessionStore`, embedded in forms, verified in `deps.py` on POST/PUT/DELETE.
- Add `app/services/dashboard_service.py` and expose `GET /api/v1/dashboard` (single aggregate view model `{status, stats, activity, docs}`) plus `GET /api/v1/status` for API/monitoring consumers. Absorbs SQL from `app/ui/dashboard.py`.
- Keep `/ui/*` fragment URLs. Keep all existing backend modules in place (no `app/backend/` rename).
- Add `httpx` as an explicit dependency. Production already runs the app lifespan (DB pool, observability); only tests that drive the in-process `ASGITransport` client need to enter lifespan via `LifespanManager`/`TestClient`.
- Supersede in-progress changes `add-web-login-form` and `fix-query-ui-crash-and-drift`; cherry-pick any must-ship bugfixes separately.

## Capabilities

### New Capabilities
- `frontend-backend-boundary`: The enforced separation between the render-only frontend package and the JSON-only backend, including the import contract and architecture test.
- `web-session-auth`: Server-side browser session authentication — `/api/v1/auth/me`, opaque session cookie, per-session CSRF tokens, and `POST /logout`.
- `dashboard-api`: JSON endpoints `GET /api/v1/status` and the aggregate `GET /api/v1/dashboard` view model.
- `evaluation-api`: JSON-only evaluation endpoints with the HTML/content-negotiation path removed.

### Modified Capabilities
- `api-authentication`: Adds the `GET /api/v1/auth/me` identity endpoint and establishes that the browser authenticates via a server-side session while the frontend forwards the API key to the backend.

## Impact

- **Code**: `main.py` (composition root wiring, lifespan); new `app/frontend/**`; removal of `app/ui/**`; `app/api/v1/endpoints/eval.py` (HTML removal); new `app/api/v1/endpoints/auth.py` and dashboard/status endpoints; new `app/services/dashboard_service.py`; `app/templates/**` and `app/static/**` relocated under `app/frontend/`; `tests/test_architecture.py` (new).
- **APIs**: `GET /api/v1/auth/me` (new), `GET /api/v1/status` (new), `GET /api/v1/dashboard` (new); eval endpoints become JSON-only; `/ui/*` unchanged in URL but reimplemented as frontend views.
- **Dependencies**: add `httpx` explicitly; `jinja2` becomes frontend-only.
- **Security**: API key no longer exposed to the browser; cookie auth introduces CSRF token requirements.
- **Constraint**: server-side in-memory sessions require `APP_WORKERS=1` (matches existing in-process `_eval_jobs` limitation).
