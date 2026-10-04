## 1. Phase 0 — De-risk (hard gate, no production changes)

- [x] 1.1 Spike `httpx.ASGITransport` against the FastAPI app: confirm middleware runs, responses serialize, and no request recurses into frontend routes; verify by logging one `/api/v1/health`-style call from a scratch script
- [x] 1.2 Confirm `ASGITransport` does not run FastAPI lifespan and that the DB pool is available under it; verify by asserting a DB-backed call succeeds only when lifespan is entered (`LifespanManager`/`TestClient`)
- [x] 1.3 Spike server-side session cookie + per-session CSRF round-trip through a real HTMX form POST; verify the POST succeeds with the token and returns HTTP 403 without it
- [x] 1.4 Record spike outcomes in `design.md` and stop if the gate fails

## 2. Phase 1 — Scaffold boundary

Execution order: 2.1 → 2.4 → 2.5 → 2.3 → 2.7 → 2.2 → 2.6 (keep the tree runnable at each step).

- [x] 2.1 Create `app/frontend/` package with `api_client.py`, `session.py`, `csrf.py`, `deps.py`, and `views/__init__.py`; verify the package imports cleanly
- [x] 2.2 Move `app/templates/` and `app/static/` under `app/frontend/` and update `Jinja2Templates`/`StaticFiles` paths; verify pages and static assets still load (isolate as its own commit after scaffolding)
- [x] 2.3 Implement `BackendClient` (httpx `ASGITransport`) and wire it onto `app.state.backend_client` **inside the existing lifespan** (not at module scope); verify a frontend view can call `/api/v1/config` through it
- [x] 2.4 Implement `SessionStore` interface + `InMemorySessionStore` with TTL and `create/get/delete/cleanup`; verify unit tests for create, expiry, and delete
- [x] 2.5 Implement CSRF: session token generation, `<meta name="csrf-token">` rendering, the global HTMX header hook, a short-lived pre-session login token issued on `GET /login`, and server-side verification; the template helper MUST handle both cases (pre-session token on `GET /login`, session token elsewhere) so 4.1 needs no second path; verify non-GET requests carry `X-CSRF-Token` and `POST /login` is rejected (403) without a valid pre-session token
- [x] 2.6 Add `tests/test_architecture.py` scanning imports for the boundary contract. **Phase 1 scope: enforce the frontend→backend rule only; mark the backend-imports-jinja rule `xfail` until 3.4 strips `eval.py` HTML, then widen it in Phase 2.** Verify it passes on a clean tree and fails on an injected frontend violation
- [x] 2.7 Add `httpx` as an explicit dependency in `pyproject.toml`; verify `uv sync` installs and imports succeed

## 3. Phase 2 — Backend JSON contract

- [x] 3.1 Add `GET /api/v1/auth/me` returning `{tenant_id, key_id}` and clean `401`; verify valid, `DEV_API_KEY`, and invalid cases against the spec
- [x] 3.2 Extract dashboard SQL from `app/ui/dashboard.py` into `app/services/dashboard_service.py`; verify the service returns status/stats/activity/docs for a tenant
- [x] 3.3 Add `GET /api/v1/status` and aggregate `GET /api/v1/dashboard`; verify JSON shape, tenant scoping, and `401` without a key
- [x] 3.4 Strip HTML from `app/api/v1/endpoints/eval.py` (remove inline Jinja, `_render_result_card`, `HX-Trigger`, `HTMLResponse`, and the card endpoint); verify every eval endpoint returns JSON with and without `HX-Request`. **Intentional window: the legacy eval UI (`app/ui/eval_ui.py`) breaks from here until 4.9 migrates it — do not treat as a regression and do not manually test eval UI until then**
- [x] 3.5 Align prompt endpoints so list/get return content the editor needs; verify list and single-get responses cover the UI's fields

## 4. Phase 3 — Migrate frontend views

> **Strangler rule (4.3-4.10):** both `app/ui` and `app/frontend` mount at `/`, so a path must never exist in both routers. Each domain is migrated and its paired `app/ui` handler deleted **in the same commit**. No double-mount, no dead handlers.

- [x] 4.1 Add frontend auth views: `GET /login`, `POST /login` (validate via `/api/v1/auth/me`, create session), `POST /logout`; verify valid/invalid/dev login and POST-only logout (GET → 405)
- [x] 4.2 Add session dependency + login redirect to `app.frontend` routes only; verify unauthenticated frontend routes return 302 to `/login`. **Scope: protects `app.frontend` routes only. `app/ui` routes remain API-key-guarded by the app-wide middleware until Phase 4; full frontend protection arrives once `app/ui` is gone and the middleware is narrowed (5.2)**
- [x] 4.3 Migrate page shells (`/`, `/config`, `/ingest`, `/query`, `/logs`, `/eval`, `/prompts`) to render-only frontend views; **delete the paired `app/ui` page route in the same commit**; verify pages render and `/` is served by `app.frontend` (slices: `/`+`/config`, `/ingest`, `/logs`, `/eval`, `/query`, `/prompts`; `/eval`+`/query` fetch initial data via `api_client` per D12)
- [x] 4.4 Migrate dashboard fragments to call `/api/v1/dashboard` via `api_client`; **delete the paired `app/ui/dashboard.py` handlers in the same commit**; verify status/stats/activity/docs fragments populate (slices: status `/api/v1/status`+`/config`; activity `/api/v1/logs/`; docs `/api/v1/ingest/files`; stats `/api/v1/dashboard`+`/config`; `app/ui/dashboard.py` deleted)
- [x] 4.5 Migrate config fragment to use `/api/v1/config` (curated config, not raw `settings`); **delete the paired `app/ui/config.py` fragment handler in the same commit**; verify the page renders the safe fields
- [x] 4.6 Migrate ingest views (form fragments + file/url/custom handlers) through `api_client`; **delete the paired `app/ui/ingest.py` handlers in the same commit**; verify all three ingestion modes still queue work. Slices: form providers → url → custom → file. Checks: every backend ingest response is `200 IngestResponse` (file/url use BackgroundTasks but still 200; custom sync 200) — verified, no dual shape handling; supported type decided by filename extension, never the forwarded content-type; upload capped at `MAX_UPLOAD_SIZE_MB` (50) → 413, mirrored by the form pre-check; `source_name` is vector metadata only (no filesystem path, no traversal); CSRF verified before every forward
- [x] 4.7 Migrate query views (`/ui/query/chat`, thread load) through `api_client`, moving `enrich_query` to the backend call; **delete the paired `app/ui/query.py` handlers in the same commit**; verify chat append and thread switching. Slices: thread-history GET → chat POST → thread-list refresh. Checks: `/api/v1/conversations/{id}` already returns `role`/`content` (no Phase 2 gap for the rendered fields); conversation context comes only from the `thread_id` form field (no frontend store), `enrich_query` already lives in the API layer; chat errors render to a `#chat-error` banner via `HX-Retarget` (backend 4xx/5xx → 200 swap) instead of a fake assistant message; CSRF verified before the forward; thread-list refresh was absent before and is intentionally not added
- [ ] 4.8 Migrate observability fragments (list + stats) through `api_client`; **delete the paired `app/ui/observability.py` handlers in the same commit**; verify filtering, pagination, and debounced submit
- [ ] 4.9 Migrate eval views (run, progress polling, results, compare) through `api_client`; **delete the paired `app/ui/eval_ui.py` handlers in the same commit**; verify 2s polling and completion refresh render from JSON
- [ ] 4.10 Migrate prompts views (list, edit, new, save, delete) through `api_client` with CSRF on writes; **delete the paired `app/ui/prompts.py` handlers in the same commit**; verify CRUD and default-prompt protections
- [ ] 4.11 Remove browser API-key code from `base.html` and `login.html`; verify the browser stores no key and login is a normal form POST

## 5. Phase 4 — Remove legacy UI

- [ ] 5.1 Delete the remaining `app/ui/**` (router + package) and update `main.py` / imports; verify the app starts with no references to `app.ui`
- [ ] 5.2 Narrow `AuthMiddleware` to `/api/v1/*` only and remove the frontend-path exemptions (D3). **Apply only after every route is owned by `app.frontend` (4.3-4.10 + 5.1)**. Verify browser routes (`/`, `/ui/*`) are guarded by the frontend session layer and no longer intercepted by API-key middleware, while `/api/v1/*` still returns 401 without a key
- [ ] 5.3 Remove all remaining `HX-Request` branches from the backend; verify `grep -R "HX-Request"` returns only frontend template usage, none in `app/api`
- [ ] 5.4 Run `git status` to check whether the Phase 1 move left `app/templates`/`app/static` behind; if present, delete them along with orphaned partials; verify no dangling path references remain
- [ ] 5.5 Update `AGENTS.md` architecture notes to describe the frontend/backend boundary and new endpoints; verify the doc matches the tree

## 6. Phase 5 — Verification

- [ ] 6.1 Run `ruff check . && ruff format .` and resolve all findings
- [ ] 6.2 Run `pytest` including `tests/test_architecture.py`; verify all pass
- [ ] 6.3 Manual checklist: login/logout, every page, every fragment, eval polling, prompts CRUD, logs filter/pagination, ingest file/url/custom
- [ ] 6.4 Postman check: every `/api/v1/*` endpoint returns JSON (never HTML), including eval with `HX-Request: true`
- [ ] 6.5 DevTools check: browser requests never target `/api/v1/*` and never expose the API key
- [ ] 6.6 Confirm `APP_WORKERS=1` in deployment config and document the session-store limitation

## 7. Follow-ups (deferred decisions)

- [ ] 7.1 Decide whether `/api/v1/config` should filter internal hosts (`REMOTE_LLAMACPP_URL`, `OLLAMA_BASE_URL`, `OTEL_EXPORTER_ENDPOINT`) for non-operator or limited-scope keys. Not a current leak (any principal that can read `/config` already has the API key), but it becomes one if a read-only/limited key or a broader-audience config view is introduced. If such a view is added, filter the fragment and the API in the same commit, never one alone.
