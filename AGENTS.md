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

## Architecture Notes

*   **Dual-Routed Application:** The app serves both a REST API at `/api/v1` and a server-rendered UI at `/` using Jinja2 templates and HTMX (see `app/ui/` and `app/templates/`).
*   **Modular API Design:** The API is versioned and modularized. Add new endpoints in `app/api/v1/endpoints/` and register them in `app/api/v1/api.py`.
*   **FastAPI Dependencies:** All FastAPI `Depends()` wiring is centralized in `app/core/dependencies.py`.
*   **Structured Models:** API requests are in `app/models/api_requests.py` and responses are in `app/models/api_response.py`.
*   **Dynamic Vector Tables:** The system automatically creates database tables (e.g., `rag_vectors_512`) based on embedding dimensions.
*   **Domain-Specific Prompts:** System and User prompts are segregated into `app/prompts/system/` and `app/prompts/user/`. Use `load_prompt(name, category)` from `app.core.prompt_loader` to fetch them (defaults to `system`).
*   **Frontend Integration:** A dedicated `GET /api/v1/config` endpoint provides non-sensitive configuration (defined in `app/models/frontend_config.py`) for frontend clients (e.g., the built-in Jinja2/HTMX UI).
*   **Dynamic Query Translation:** Translation strategies (Multi-Query, HyDE, etc.) load their prompts dynamically from the `prompts/` subdirectories, allowing customization without code changes.
*   **External Application Integration:** Standalone consumer scripts (e.g., validators) are placed in `scripts/` and interact with the RAG API over HTTP, not as part of the core `app/` logic.

## Conventions

*   **Virtual Environment & Dependencies:** Use `uv` for managing the Python environment and dependencies.
*   **Configuration:** All environment variables for configuration are managed via a `.env` file in the root directory.
*   **New Vector DB Implementations:** Must inherit from `app.core.interfaces.BaseVectorDB`.
*   **New Domain Prompts:** Place new `.md` prompt files in `app/prompts/system/` or `app/prompts/user/`.
*   **External Scripts:** Place any scripts that consume the RAG API (e.g., data validators, batch processors) in the `scripts/` directory.

## Setup & Environment Quirks

*   **Python Version:** Requires Python 3.12+.
*   **Docker:** Essential for local development if using the PGVector database.
*   **API Key:** An `OPENAI_API_KEY` is required.
*   **Local LLM:** If using a local LLM, `LOCAL_MODEL` in `.env` may point to the GGUF model file. If unset, the system auto-detects `.gguf` files in `models/`.
*   **System Prompt:** The `SYSTEM_PROMPT_FILE` in `.env` determines which prompt from `app/prompts/` is used.
