# AGENT GUIDANCE FOR RAG FRAMEWORK

This document provides high-signal instructions for working in this repository.

## Developer Commands

*   **Install Dependencies:**
    ```bash
    uv venv
    source .venv/bin/activate # Windows: .venv\Scripts\activate
    uv sync
    ```
*   **Run API:**
    ```bash
    python main.py
    ```
*   **Start Local PGVector Database (with Docker):**
    ```bash
    docker run -d \
      --name rag-postgres \
      -e POSTGRES_USER=user \
      -e POSTGRES_PASSWORD=password \
      -e POSTGRES_DB=rag_db \
      -p 5432:5432 \
      -v rag_data:/var/lib/postgresql/data \
      pgvector/pgvector:pg16
    ```
*   **Download Local Llama Model (GGUF):**
    ```bash
    huggingface-cli download NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF \
      Hermes-2-Pro-Llama-3-8B-Q4_K_M.gguf \
      --local-dir models
    ```
*   **Code Formatting:**
    ```bash
    ruff check .      # lint
    ruff format .     # format
    ```
*   **UAT / Manual Verification:** Follow `docs/uat-checklist.md`. Seed data is a
    precondition — a `200` on an empty table does not exercise row-processing paths.

## Architecture Notes

*   **Split Frontend / Backend:** The backend is a JSON-only API under `/api/v1` (`app/api/`). The browser UI is server-rendered Jinja2 + HTMX under `app/frontend/` and reaches the backend exclusively over HTTP through `app/frontend/api_client.py` (`httpx.ASGITransport`). The backend never renders HTML; the frontend never imports backend internals.
*   **Import Wall:** `tests/test_architecture.py` enforces the boundary with an AST import scan: the frontend may import only `app.core.config`, `app.core.csrf`, and `app.core.sessions` from `app`, and the backend must not import `jinja2`, `starlette.templating`, `app.frontend`, or `app.ui`.
*   **Frontend Package:** Pages and fragments live in `app/frontend/views/`; templates in `app/frontend/templates/` (`pages/` + `partials/`); static assets in `app/frontend/static/`. Frontend dependencies (`get_backend_client`, `require_session`, `verify_session_csrf`) live in `app/frontend/deps.py`.
*   **Auth & Sessions:** The browser never holds the API key. `POST /login` validates it against `GET /api/v1/auth/me` and stores it in a server-side session (`app/core/sessions.py`); the browser only gets an opaque HttpOnly cookie. `AuthMiddleware` guards only `/api/v1/*` (JSON `401`); browser routes are guarded by `require_session`.
*   **CSRF:** A `<meta name="csrf-token">` plus a global HTMX hook adds `X-CSRF-Token` to non-GET requests; the frontend verifies it (`verify_session_csrf`). `POST /login` uses a short-lived pre-session token.
*   **HTMX Error Idiom (D13):** A failing fragment returns `200` with `HX-Retarget: #<domain>-error` and `HX-Reswap: innerHTML` plus an error partial, so HTMX swaps the error into a banner instead of the primary target; never render errors into the primary target.
*   **Modular API Design:** The API is versioned and modularized. Add new endpoints in `app/api/v1/endpoints/` and register them in `app/api/v1/api.py`.
*   **FastAPI Dependencies:** All FastAPI `Depends()` wiring is centralized in `app/core/dependencies.py`.
*   **Structured Models:** API requests are in `app/models/api_requests.py` and responses are in `app/models/api_response.py`.
*   **Dynamic Vector Tables:** The system automatically creates database tables (e.g., `rag_vectors_512`) based on embedding dimensions.
*   **Domain-Specific Prompts:** System and User prompts are segregated into `app/prompts/system/` and `app/prompts/user/`. Use `load_prompt(name, category)` from `app.core.prompt_loader` to fetch them (defaults to `system`).
*   **Frontend Config:** A dedicated `GET /api/v1/config` endpoint provides non-sensitive configuration (defined in `app/models/frontend_config.py`) to the frontend, which fetches initial page data over the API.
*   **Dynamic Query Translation:** Translation strategies (Multi-Query, HyDE, etc.) load their prompts dynamically from the `prompts/` subdirectories, allowing customization without code changes.
*   **External Application Integration:** Standalone consumer scripts (e.g., validators) are placed in `scripts/` and interact with the RAG API over HTTP, not as part of the core `app/` logic.

## Conventions

*   **Virtual Environment & Dependencies:** Use `uv` for managing the Python environment and dependencies.
*   **Configuration:** All environment variables for configuration are managed via a `.env` file in the root directory.
*   **New Vector DB Implementations:** Must inherit from `app.core.interfaces.BaseVectorDB`.
*   **New Domain Prompts:** Place new `.md` prompt files in `app/prompts/system/` or `app/prompts/user/`. The category is validated to `system`/`user` (path traversal guard).
*   **Boundary Discipline:** A UI fragment may only be added under `app/frontend/` and must call the backend via `api_client`; a new capability belongs in `app/api/v1/endpoints/`, not in a view. Never let a path exist in both the frontend and backend.
*   **External Scripts:** Place any scripts that consume the RAG API (e.g., data validators, batch processors) in the `scripts/` directory.

## Setup & Environment Quirks

*   **Python Version:** Requires Python 3.12+.
*   **Workers:** The frontend session store is in-memory, so run with `APP_WORKERS=1`.
*   **Docker:** Essential for local development if using the PGVector database.
*   **API Key:** An `OPENAI_API_KEY` is required.
*   **Local LLM:** If using a local LLM, `LOCAL_MODEL` in `.env` may point to the GGUF model file. If unset, the system auto-detects `.gguf` files in `models/`.
*   **System Prompt:** The `SYSTEM_PROMPT_FILE` in `.env` determines which prompt from `app/prompts/` is used.

## Deferred Decisions

*   **`/api/v1/config` host exposure:** `/api/v1/config` exposes internal host URLs (`REMOTE_LLAMACPP_URL`, `OLLAMA_BASE_URL`, `OTEL_EXPORTER_ENDPOINT`). Not a leak today — every API key is operator-scope, so anyone who can read `/config` can already read these via `/api/v1/config`. It becomes a real exposure if limited-scope or read-only keys are introduced; if they are, filter both the API response and the config fragment in the same change. See archived change `separate-ui-from-backend`, task 7.1.
