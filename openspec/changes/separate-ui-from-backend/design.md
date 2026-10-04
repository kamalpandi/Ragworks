## Context

See `proposal.md` for motivation. Relevant current-state facts that shape the approach:

- One FastAPI process (`main.py`) mounts `api_router` at `/api/v1` and `ui_router` at `/`, with app-wide `AuthMiddleware`, `RateLimitMiddleware`, `ObservabilityMiddleware`, `CORSMiddleware`, and a `lifespan` that initializes the DB pool, migrations, and the log store.
- `AuthMiddleware` (`app/middleware/auth.py`) already supports `X-API-Key`, `Authorization: Bearer`, the `rag_api_key` cookie, and `DEV_API_KEY`, and redirects HTML `Accept` requests to `/login`.
- `scripts/*` call `/api/v1/*` with JSON bodies and multipart file uploads; the bundled UI's HTMX forms currently send form-encoded bodies and rely on `HX-Request` sniffing in `app/api/v1/endpoints/eval.py`.
- `APP_WORKERS` defaults to `1`; eval run state (`_eval_jobs`) is already in-process.
- `httpx` is used by scripts but is only a transitive dependency. `jinja2` is a declared dependency.

## Goals / Non-Goals

**Goals:**
- A single enforceable boundary: backend JSON-only, frontend render-only, connected via HTTP.
- Keep the existing HTMX + Jinja UI behavior and `/ui/*` URLs while removing all business logic from the UI layer.
- Remove the API key from the browser.
- Lowest-churn path: no mass rename of backend modules, no DB schema change.

**Non-Goals:**
- Splitting into separate deployable services (topology B).
- Replacing HTMX with a client-side framework.
- Postgres/Redis-backed session persistence (deferred; interface only).
- Renaming `/ui/*` to `/fragments/*`.

## Decisions

### D1: One process, logical split, enforced import wall
Keep backend modules where they are; add `app/frontend/`. Enforce with an automated check.
- **Why**: the guarantee comes from the contract, not directory nesting; a full `app/backend/` rename is high-churn, low-value.
- **Alternatives**: (B) two services — rejected for now (ops/CORS/auth hop); full rename — rejected as pure churn.

### D2: Frontend reaches backend via `httpx.ASGITransport`
`app/frontend/api_client.py` wraps an `httpx.AsyncClient(transport=ASGITransport(app=...), base_url=...)`; the backend ASGI app instance is injected at composition time and stored on `app.state`, so the frontend never imports `main` or backend internals.
- **Why**: real HTTP request/response semantics (middleware, serialization) with no network and no Python coupling.
- **Alternatives**: loopback TCP — needs a listening socket, awkward in tests; direct service calls — reintroduces coupling.
- **Lifespan caveat**: `ASGITransport` does not run FastAPI lifespan. In production the serving process already runs the app lifespan (DB pool up). In tests, lifespan must be entered explicitly via `LifespanManager` or `TestClient`. **Phase 0 gate**: prove this before Phase 1.

### D3: Middleware narrows to the API; frontend enforces sessions
Today `AuthMiddleware` is app-wide and validates every non-exempt path with an API key. This change narrows it to run only for requests under `/api/v1/*`; everything else (including `/metrics`, `/health`, `/login`, and all browser-facing routes) is outside its scope. Browser-facing frontend routes (`/`, `/ui/*`, page shells) are guarded by the frontend session layer and redirect to `/login`.
- **Why**: the browser no longer holds an API key, so API-key middleware must not run on those paths.
- **Alternatives**: keep app-wide middleware and add frontend paths to the exempt list — rejected, because it grows a fragile list and leaves the middleware's intent unclear; a prefix scope is explicit and self-maintaining.
- **Consequence**: the spec `api-authentication` is modified (both the middleware scope requirement and the exempt-endpoints requirement).

### D4: `auth/me` reuses middleware instead of an exempt auth endpoint
`GET /api/v1/auth/me` returns `{tenant_id, key_id}` for the presented key. Login submits the key to the backend through this endpoint.
- **Why**: no new exempt path, no duplicated `validate_api_key` logic, `DEV_API_KEY` handled by existing middleware.
- **Alternatives**: exempt `POST /auth/session` with a body key — rejected.

### D5: In-memory `SessionStore` behind an interface, in shared `app.core.sessions`
Opaque session id in an `HttpOnly`, `SameSite=Lax`, `Secure`(prod) cookie; session data (`api_key`, `tenant_id`, TTL) server-side. `create/get/delete/cleanup`.
- **Why**: matches topology A and `APP_WORKERS=1`.
- **Shared, not frontend-owned**: `SessionStore` lives in `app.core.sessions` because it is a server-side concern used by both the frontend (create/read) and `AuthMiddleware` (resolve the API key for browser routes). `app.frontend` may import `app.core.sessions` alongside `app.core.config`; the middleware imports it as an internal backend module. This keeps "the key never reaches the browser" true from 4.1, not just from 4.11.
- **Bridge**: for non-`/api/v1/*` requests with no presented key, `AuthMiddleware` looks up the session cookie and treats the session's `api_key` as presented (then validates it as usual).
- **Alternatives**: signed client-side cookie (Starlette `SessionMiddleware`) — rejected, puts key material in the browser; Postgres-backed — deferred.
- **Constraint**: requires `APP_WORKERS=1`; documented and pinned.

### D6: Per-session CSRF token via header, plus a pre-session token for login
Render the session token into a `<meta name="csrf-token">`; a small global HTMX hook adds `X-CSRF-Token` to every non-GET request; the frontend dependency verifies it on POST/PUT/DELETE. Because `POST /login` runs before a session exists, `GET /login` issues a short-lived pre-session CSRF token (signed/double-submit) that the login POST must present.
- **Why**: minimal template churn versus hidden inputs in every form; keeps verification server-side and centralized; closes the login-CSRF hole (an attacker otherwise could log a victim into the attacker's account).
- **Alternatives**: hidden inputs per form — more churn; `SameSite` only — rejected as insufficient; exempting login from CSRF — rejected, leaves login CSRF unprotected.

### D7: `POST /logout` with CSRF; no `GET /logout`
Logout invalidates the server-side session and clears the cookie.

### D8: Dashboard is one aggregate endpoint plus `/status`
`GET /api/v1/dashboard` returns a single view model `{status, stats, activity, docs}` scoped to the tenant, composed in `app/services/dashboard_service.py`. `GET /api/v1/status` is a separate lightweight status endpoint.
- **Why**: keeps the frontend dumb (one call, one render) and avoids a chatty dashboard.
- **Guardrail**: the aggregate is a dashboard view model, not a general-purpose query endpoint.

### D9: Evaluation API is JSON-only
Remove `HX-Request` branches, inline Jinja, `_render_result_card`, `HX-Trigger`, and the HTML card endpoint from `app/api/v1/endpoints/eval.py`. The frontend polls a frontend fragment that proxies the JSON progress endpoint and renders a template; completion-triggered refresh is driven by the frontend response.
- **Why**: backend must not render HTML; content negotiation is the gray area being removed.

### D10: Enforce the contract with an AST test (no new tooling)
`tests/test_architecture.py` scans imports: frontend may import only `app.core.config` among backend modules; backend must not import `jinja2`, `starlette.templating`, or `app.frontend`.
- **Alternative**: `import-linter` (new dev dependency) — viable, deferred; AST test adds nothing to the dependency graph.

### D11: Keep `/ui/*`; relocate templates/static under `app/frontend/`
URLs are cosmetic; ownership of templates/static is not. Move `app/templates` and `app/static` into `app/frontend/`.

### D12: Data-bearing page shells fetch initial data over the API
`/eval` and `/query` are not pure shells: `eval.html` renders the metric checkboxes (`eval.html:11`) and thread dropdown (`eval.html:49,60`); `query.html` renders the file datalist (`query.html:66`), thread dropdown (`query.html:77`), and prompt dropdown (`query.html:108`). Today `app/ui/eval_ui.py:15-29` and `app/ui/query.py:19-22` compute these from backend internals.
- **Decision**: the frontend shell handler obtains them via `api_client` (`GET /api/v1/eval/metrics`, `/api/v1/eval/results`, `/api/v1/conversations`, `/api/v1/prompts`, `/api/v1/ingest/files`) using the session key, then renders. This keeps the shell free of backend imports while preserving first-paint content.
- **Alternative (deferred)**: render the shell empty and load option lists via HTMX fragments (like the dashboard). Cleaner separation and progressive loading, but requires new frontend fragment endpoints; only worth it if first-paint orchestration proves costly.
- **Rule**: a shell may call the API; it may not import backend modules. Multi-call shells are candidates for later fragmentization.

### D13: HTMX error idiom — retarget to a banner, return 200
A failing frontend fragment (chat, eval run, prompt save, log clear) returns HTTP 200 so HTMX performs the swap, with `HX-Retarget: #<domain>-error` and `HX-Reswap: innerHTML`, and a small error partial body. The frontend maps the backend's 4xx/5xx `detail` to a friendly title/message; the banner is cleared on `htmx:beforeRequest`.
- **Why**: HTMX does not swap non-2xx responses by default, so returning the backend status silently drops the error; rendering into the default target would append a fake success-style node (e.g. a fake assistant message).
- **Rule**: every POST-capable fragment gets a dedicated error container and the same retarget pattern; never render errors into the primary target.

## Risks / Trade-offs

- **In-memory sessions break with `APP_WORKERS > 1`** → pin/validate `APP_WORKERS=1`; keep `SessionStore` an interface for later Postgres/Redis.
- **`ASGITransport` lifecycle mismatch** → Phase 0 hard gate; use `LifespanManager`/`TestClient` in tests; production lifespan already runs.
- **AuthMiddleware scope change** could leave frontend routes unguarded during migration → frontend session dependency is added in the same phase routes are moved; temporary overlap while `app/ui` still exists.
- **CSRF integration with HTMX** (GET vs non-GET, `hx-include`) → single global hook adds the header; GETs unaffected; covered by tests.
- **Extra in-process JSON hop** per fragment → negligible for an admin UI; measured in Phase 0 spike.
- **Template/static path move** → update `Jinja2Templates` and `StaticFiles` in one phase; grep for stale paths.
- **Regression risk from deleting `app/ui`** → strangler sequencing (frontend added alongside, switch over domain-by-domain, delete last); git revert is the rollback.

## Migration Plan

1. **Phase 0 (gate)** — spike `ASGITransport` + lifespan and session cookie + CSRF through an HTMX form. No production code changes.
2. **Phase 1** — scaffold `app/frontend/` (client, session, csrf, deps), move templates/static, wire `app.state.backend_client`, add architecture test.
3. **Phase 2** — backend: `/auth/me`, `dashboard_service`, `/status`, `/dashboard`; strip eval HTML; add `httpx` dependency.
4. **Phase 3** — migrate views domain-by-domain (pages, then dashboard, config, ingest, query, logs, eval, prompts); switch templates over.
5. **Phase 4** — delete `app/ui`, remove browser key code and old template/static dirs.
6. **Phase 5** — verify (ruff, pytest, manual checklist, Postman JSON-only, DevTools no `/api/v1` from browser).

**Rollback**: no schema changes; revert the migration commit(s) to restore `app/ui`. Deployment requires `APP_WORKERS=1`.

## Phase 0 Spike Results (gate passed)

Run against Python 3.12.11, FastAPI 0.128.2, httpx 0.28.1, Starlette 0.50.0, with a live local Postgres.

**1.1 / 1.2 — `ASGITransport` + lifespan**

- `ASGITransport` does **not** run FastAPI lifespan: a minimal app reported `lifespan_ran: false`; entering `app.router.lifespan_context(app)` flipped it to `true`.
- Real app: `get_pool()` raised `RuntimeError` before lifespan; `/health` returned `{"status": "degraded", "database": "disconnected"}` without lifespan; after entering `app.router.lifespan_context(app)` the pool initialized and `/health` returned `{"status": "healthy", "database": "connected"}`.
- Middleware runs through `ASGITransport`: `/api/v1/config` with no key returned `401` (`application/json`); an unknown `/api/v1/*` path also returned `401` before routing; no recursion into frontend routes.
- **Conclusion**: production (uvicorn) runs lifespan once and the module-level pool is shared by in-process client calls; tests must enter lifespan explicitly (no extra dependency required — `app.router.lifespan_context` works; `asgi-lifespan` is not installed).

**1.3 — session + CSRF prototype**

- `GET /login` issues a pre-session token; `POST /login` without it → `403` (no session).
- `POST /login` with it → `302` + `Set-Cookie: rag_session=<opaque>; HttpOnly; Path=/; SameSite=lax`; the cookie contains no API key.
- Authenticated `POST /action` without session CSRF → `403`; with the session token → `200`.
- After deleting the server-side session, the same request → `401`.
- **Conclusion**: the server-side session + pre-session/session CSRF model works end-to-end over an in-process client. Gate cleared; proceed to Phase 1.

Spike scripts were throwaway (temp dir), not added to the repo.

## Open Questions

- Session TTL value (default proposal: ~8 hours) — tune later.
- Whether to persist sessions in Postgres — deferred until `APP_WORKERS > 1` or multi-instance is needed.
- Whether to add `import-linter` alongside the AST test — optional hardening.
