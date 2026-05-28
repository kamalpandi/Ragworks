# Modular RAG Framework

**A vendor-agnostic, production-ready Retrieval-Augmented Generation pipeline built with FastAPI, PostgreSQL (PGVector), and Pinecone.**

## Project Overview

This framework provides a robust backend for RAG applications, designed with a strict "Separation of Concerns" philosophy. Unlike tightly coupled RAG scripts, this project uses an interface-based architecture that allows developers to swap components (Vector Databases, Embedders, LLMs) with zero friction.

**Core Value Proposition:**

- **Dual-Database Strategy:** Develop locally using **PGVector** (Docker) for zero cost and total privacy, then deploy to **Pinecone** for cloud scalability—toggled via a single environment variable.
- **Asynchronous Processing:** Heavy ingestion tasks (PDF parsing, semantic chunking) run via FastAPI Background Tasks to prevent API blocking.
- **Layout-Aware Parsing:** Utilizes `pdfplumber` to correctly handle multi-column layouts and tables in financial/technical documents.
- **Fintech-Optimized Parsing:** Uses a "Crop & Stitch" algorithm to detect PDF tables, convert them to **Markdown**, and preserve their context for superior LLM reasoning.
- **Self-Healing Ingestion:** A modular chunking engine with a safety layer that automatically detects and splits oversized chunks to prevent API errors.
- **Hybrid Deployment:** Develop locally with **Llama 3** (via `llama.cpp`) and **PGVector** for zero cost, then scale to OpenAI and Pinecone with a config switch.
- **Dynamic Vector Store:** Automatically creates database tables based on embedding dimensions (e.g., `rag_vectors_512`), allowing you to mix OpenAI, Cohere, and Local models in the same system without schema conflicts.
- **Domain-Specific Prompting:** Swap system prompts per use case via a single config variable — no code changes required.
- **External Validator Apps:** A clean HTTP interface allows external scripts and services to use the RAG system as a knowledge backend.

## System Architecture

The system is built on a modular pipeline architecture.

```mermaid
graph LR
    User[Client] --> API[FastAPI Routes]
    ExternalApp[External App e.g. Email Validator] --> API
    API --> Ingest[Ingestion Service]
    API --> Engine[RAG Engine]

    subgraph "Smart Data Pipeline"
    Ingest --> Parser[Layout-Aware PDF Parser]
    Parser --> ChunkingFactory[Chunking Factory]
    ChunkingFactory --> Embedder[OpenAI/Local Embedder]
    Embedder --> VectorDB[PGVector / Pinecone]
    end

    subgraph "Inference Pipeline"
    Engine --> Embedder
    Engine --> VectorDB
    VectorDB --> LLM[Local Llama / OpenAI / Ollama]
    end
```

## Features

- **[+] Vendor Agnostic:** Native support for both `PGVector` (Local) and `Pinecone` (Cloud).
- **[+] Metadata Filtering:** Precise retrieval using file-level filters (e.g., query only within `prospectus.pdf`).
- **[+] Duplicate Detection:** Logic to prevent redundant context from polluting the LLM window.
- **[+] Multi-Dimensional Storage:** The system detects your embedding model's output size (e.g., 1536 vs 512) and dynamically generates the correct SQL tables (`rag_vectors_1536`, `rag_vectors_512`).
- **[+] Vector Slicing:** Automatically truncates OpenAI vectors to smaller dimensions (e.g., 512) to reduce storage costs by **66%** while maintaining performance.
- **[+] Markdown Table Extraction:** Extracts tables from PDFs and converts them to Markdown format, ensuring LLMs can "read" financial data row-by-row.
- **[+] Context Preservation:** Preserves the text immediately surrounding tables so the LLM knows _what_ the data represents.
- **[+] Recursive Strategy:** (Default) Robust splitting for data-heavy documents.
- **[+] Paragraph Strategy:** (Optional) Splits on paragraph boundaries with overlap — ideal for well-structured prose.
- **[+] Semantic Strategy:** (Optional) AI-driven splitting based on topic changes.
- **[+] Safety Guardrails:** A dedicated `TokenSafetyEnforcer` catches chunks that exceed model limits (e.g., >8192 tokens) and recursively splits them before API calls.
- **[+] Ollama Support:** Drop-in integration with locally-hosted Ollama models via `LLM_PROVIDER=ollama`.
- **[+] Local LLM Support:** Native integration with `llama-cpp-python` for running quantized models (GGUF) on CPU/Apple Silicon.
- **[+] Async Wrapper:** Runs synchronous local inference in non-blocking threads to keep the API responsive.
- **[+] Centralized Dependency Injection:** All FastAPI dependencies live in `core/dependencies.py` — zero wiring logic in route files.
- **[+] Domain-Specific System Prompts:** Load per-domain prompts from `app/prompts/system/` via a single `SYSTEM_PROMPT_FILE` env variable. No hardcoded prompts in code.
- **[+] Query Enrichment:** Automatic intent detection and vague-query rewriting before retrieval — no config needed.
- **[+] HTMX Web UI:** Built-in dashboard, query chat, ingestion, and config pages powered by htmx — no JavaScript framework required.
- **[+] Frontend Configuration:** Dedicated `/api/v1/config` endpoint to expose non-sensitive backend settings to clients.
- **[+] External App Support:** The RAG system exposes a clean HTTP API, allowing external validator scripts or services to use ingested knowledge without modifying the core.

## Getting Started

### 1. Prerequisites

- Python 3.12+
- Docker (Required only if using Local PGVector)
- OpenAI API Key

### 2. Installation

Clone the repository and install dependencies. We recommend using a virtual environment.

```bash
# Clone the repo
git clone https://github.com/kamalpandiv/refactored-couscous.git

cd rag-framework

# Setup virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync
```

### 3. Configuration

Create a `.env` file in the root directory.

```ini
# --- API Keys ---
OPENAI_API_KEY=sk-your-key-here

# --- Database Selection ---
# True = PGVector (local Docker), False = Pinecone (cloud)
USE_LOCAL_DB=True
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# --- LLM Provider ---
# One of: llamacpp, openai, ollama
LLM_PROVIDER=llamacpp

# --- RAG Pipeline ---
# 'recursive', 'paragraph', or 'semantic'
CHUNKING_STRATEGY=recursive
# Number of chunks to retrieve per query
TOP_K=10
# Embedding batch size
BATCH_SIZE=32

# --- Prompt Config ---
# Name of the prompt file from app/prompts/system/ (without extension)
SYSTEM_PROMPT_FILE=default
```

### 4. Database Setup (Local Mode)

If running locally, spin up the PGVector container. This command creates a persistent volume so data survives restarts.

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

### 5. Running the API

```bash
python main.py
```

- Server running at: `http://0.0.0.0:8000`
- Swagger UI: `http://0.0.0.0:8000/docs`

## LLM Backend Setup

The framework supports three LLM backends:

| Provider    | Config Value | Requirements                                      |
| ----------- | ------------ | ------------------------------------------------- |
| **llama.cpp** | `llamacpp`   | GGUF model file in `models/` directory or remote server |
| **OpenAI**  | `openai`     | `OPENAI_API_KEY` set in `.env`                    |
| **Ollama**  | `ollama`     | `OLLAMA_BASE_URL` (default: `http://localhost:11434`) |

Set `LLM_PROVIDER` in your `.env` to switch.

### Local llama.cpp Setup

```bash
huggingface-cli download NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF \
  Hermes-2-Pro-Llama-3-8B-Q4_K_M.gguf \
  --local-dir models
```

## Usage Examples

**Ingest a File (Non-Blocking)**

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/annual_report.pdf"
```

**Ingest a URL**

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/guide"}'
```

**List Available Prompts**

```bash
curl "http://localhost:8000/api/v1/prompts"
```

**Query the Knowledge Base**

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the risks mentioned in the report?",
    "file_name": "annual_report.pdf"
  }'
```

**Query with a Translation Strategy**

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the opt-out requirements?",
    "file_name": "can_spam_guide.pdf",
    "translation_strategy": "multi_query"
  }'
```

## Web UI (htmx)

The framework includes a fully functional web interface powered by **htmx** and **Pico CSS**. It provides a dashboard, query chat, document ingestion, and configuration pages — all without writing JavaScript.

| Page     | URL         | Description                                          |
| -------- | ----------- | ---------------------------------------------------- |
| Dashboard | `/`         | System health monitoring and diagnostics              |
| Chat      | `/query`    | Ask questions against ingested documents              |
| Ingest    | `/ingest`   | Upload PDFs, scrape URLs, or paste raw text           |
| Config    | `/config`   | View non-sensitive backend configuration              |

### Query Page Features
- **Conversation Thread:** Each Q&A pair is appended — history is preserved across queries.
- **Markdown Rendering:** AI responses render code blocks, tables, and lists properly.
- **File Autocomplete:** Start typing a file name to see suggestions from ingested documents.
- **Translation Strategy Selector:** Choose from Multi-Query, HyDE, Step-Back, or RAG Fusion.
- **System Prompt Selector:** Pick from available system prompt templates or write a custom one.
- **Copy to Clipboard:** One-click copy of AI responses.
- **Keyboard Shortcut:** Press `Ctrl+Enter` to submit from the message textarea.

### Ingest Page Tabs
- **Upload Document** — PDF or TXT file (via multipart form)
- **Scrape URL** — Extract content from a web page
- **Raw Text** — Paste arbitrary text directly

All forms submit via htmx and return inline status messages — no page reloads.

## Domain-Specific System Prompts

The RAG engine supports swappable system prompts loaded from `app/prompts/system/`. This allows you to repurpose the same RAG system for different compliance domains, assistants, or use cases — without changing any code.

```
app/prompts/
├── system/
│   ├── default.md             # General-purpose assistant
│   ├── strict_context_only.md # Context-only mode (no prior knowledge)
│   ├── multi_query.md         # Multi-query translation system prompt
│   ├── hyde.md                # HyDE translation system prompt
│   ├── step_back.md           # Step-back translation system prompt
│   └── rag_fusion.md          # RAG Fusion translation system prompt
└── user/
    ├── multi_query.md         # User-side template for multi-query
    ├── hyde.md                # User-side template for HyDE
    ├── step_back.md           # User-side template for step-back
    └── rag_fusion.md          # User-side template for RAG Fusion
```

To switch domains, update your `.env`:

```ini
SYSTEM_PROMPT_FILE=default
```

**Prompt design principle:** Keep system prompts short and role-defining. The actual domain knowledge comes from retrieved chunks — do not duplicate rules in the prompt.

Example `default.md`:

```
You are a helpful assistant. Use the retrieved context to answer the user's question accurately and concisely.
If the context is relevant, base your answer on it. If it is not sufficient, you may supplement with your general knowledge.
```

For strict context-only mode (no prior knowledge), use `strict_context_only.md` instead of `default`.

## Demo Scripts

The `scripts/` directory contains standalone demo scripts that exercise the RAG API over HTTP. Run them after starting `python main.py`.

| Script | Purpose |
|--------|---------|
| `demo_full_pipeline.py` | End-to-end demo: ingests custom text, URL, and file, then runs queries with Multi-Query and HyDE strategies |
| `demo_ingest_custom.py` | Seeds a SaaS FAQ knowledge base and runs a customer support Q&A session |
| `demo_ingest_file.py` | Uploads a local PDF and runs legal NDA clause queries with HyDE |
| `demo_ingest_url.py` | Ingests a Wikipedia article and asks domain-specific questions with Multi-Query |

## Database Utilities

| Script | Purpose |
|--------|---------|
| `reset_db.py` | Drops the current PGVector table (`rag_vectors_{dim}`). Restart the app to recreate. |
| `wipe.py` | Deletes the Pinecone index by name. |

## External Validator Apps

The RAG system is designed to serve as a **knowledge backend** for external applications. External apps construct a query, call the RAG API over HTTP, and receive grounded answers — keeping the RAG system clean and reusable.

```
External App (e.g. Email Validator)
        │
        │  POST /api/v1/query
        ▼
   RAG System API
        │
        ▼
  Vector DB (ingested PDFs)
```

**Example: CAN-SPAM Email Validator**

Place external scripts in `scripts/` — they are standalone consumers of the API, not part of the core framework.

```
scripts/
├── emails/
│   └── validator.py          # CAN-SPAM email compliance checker
├── demo_full_pipeline.py     # End-to-end demo
├── demo_ingest_custom.py     # Custom text ingest demo
├── demo_ingest_file.py       # File ingest demo
└── demo_ingest_url.py        # URL ingest demo
```

```bash
# Terminal 1 — start the RAG system
python main.py

# Terminal 2 — run the validator against a sample email
python scripts/emails/validator.py
```

The validator script calls `POST /api/v1/query` with the email content and retrieves a structured compliance assessment grounded in the ingested FTC compliance guide.

## Project Structure

The codebase uses a **Modular Component Architecture** to facilitate easy contribution and component swapping.

```text
rag-framework/
├── app/
│   ├── api/                  # REST API Layer
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── config.py
│   │       │   ├── ingest.py
│   │       │   ├── list_prompts.py
│   │       │   └── query.py
│   │       └── api.py
│   ├── components/           # Interchangeable Modules
│   │   ├── chunking/         # Chunking strategies
│   │   ├── embedders/        # OpenAI embedder
│   │   ├── llms/             # LLM providers (OpenAI, Ollama, llama.cpp)
│   │   ├── loaders/          # PDF & web loaders
│   │   ├── query_translation/# Multi-Query, HyDE, Step-Back, RAG Fusion
│   │   └── vector_dbs/       # PGVector, Pinecone
│   ├── core/                 # Config, Interfaces & Dependencies
│   │   ├── config.py
│   │   ├── dependencies.py   # Centralized FastAPI Depends()
│   │   ├── interfaces.py     # Abstract base classes
│   │   └── prompt_loader.py  # Loads prompts from app/prompts/
│   ├── models/               # Data Models (API, Domain, Frontend Config)
│   ├── prompts/              # Swappable system/user prompt files (.md)
│   │   ├── system/
│   │   └── user/
│   ├── services/             # IngestionService, RAGEngine
│   ├── static/               # Static assets (htmx JS)
│   ├── templates/            # Jinja2 HTML templates (htmx UI)
│   │   ├── pages/            # Full page templates
│   │   └── partials/         # HTMX swap fragments
│   └── ui/                   # HTMX UI route handlers
├── scripts/                  # Standalone consumer scripts
│   ├── emails/
│   │   └── validator.py      # CAN-SPAM email compliance checker
│   ├── demo_full_pipeline.py
│   ├── demo_ingest_custom.py
│   ├── demo_ingest_file.py
│   └── demo_ingest_url.py
├── docs/
│   ├── README.md
│   └── openapi.yaml
├── main.py
├── pyproject.toml
└── uv.lock
```

## Query Translation Strategies

The `/query` endpoint supports optional query translation to improve retrieval quality for exploratory questions.

| Strategy      | Best For                     | How It Works                                       |
| ------------- | ---------------------------- | -------------------------------------------------- |
| `multi_query` | Broad research questions     | Generates 3 query variations, retrieves across all |
| `hyde`        | Improving recall             | Generates a hypothetical answer first, then retrieves context matching that answer |
| `step_back`   | Conceptual questions         | Abstracts to a higher-level query                  |
| `rag_fusion`  | Maximum coverage             | Generates 4 queries with RRF score merging         |
| _(none)_      | Specific lookups, validation | Uses raw query directly — fastest and most precise |

### Query Enrichment

Before any translation strategy runs, every query passes through an **intent-aware enrichment** step. The enricher:

1. **Detects intent** (summarize, explain, list, compare, how-to, why, find)
2. **Extracts the topic** from the target file name or URL
3. **Rewrites vague queries** (e.g., "what is this about?") into retrieval-friendly versions (e.g., "Provide a comprehensive summary of the main points in `annual_report.pdf`")

This happens automatically at the router level — no configuration needed.

> **Tip:** For compliance validation (e.g., checking an email against CAN-SPAM rules), omit the translation strategy. Your query already contains all the specifics needed for precise retrieval.

## Roadmap

- [ ] **Qdrant Support:** Add `QdrantDB` adapter.
- [ ] **Hybrid Search:** Implement keyword + vector search (BM25).
- [ ] **Streaming Responses:** Server-Sent Events for real-time LLM output in the UI.
- [ ] **Conversation Memory:** Maintain chat history across queries for follow-up questions.
- [x] **HTMX Web UI:** Fully interactive dashboard, query, ingest, and config pages.
- [x] **Multi-LLM Support:** OpenAI, Ollama, and local llama.cpp — swappable via config.
- [x] **Query Translation:** Multi-Query, HyDE, Step-Back, RAG Fusion strategies.
- [x] **Query Enrichment:** Automatic intent detection and vague-query rewriting.
- [x] **Centralized Dependencies:** All `Depends()` wiring in `core/dependencies.py`.
- [x] **Domain Prompt Loader:** Swappable system prompts via `app/prompts/` and `SYSTEM_PROMPT_FILE` env var.
- [x] **External App Pattern:** Clean separation between RAG core and consumer scripts.
- [x] **Dynamic Vector Tables:** Auto-scaling DB schema.
- [x] **Local LLM:** Llama 3 via `llama.cpp` + Ollama.
- [x] **Advanced PDF Parsing:** Markdown table extraction.

## Contribution Guidelines

1. **Fork & Clone:** Fork the repo and clone it locally.
2. **Branch:** Create a branch for your feature (`git checkout -b feature/new-adapter`).
3. **Code Style:** Formatted with `ruff`.
4. **Interface Compliance:** If adding a new DB, ensure it inherits from `app.core.interfaces.BaseVectorDB`.
5. **Prompt Files:** If adding a new domain prompt, place it in `app/prompts/` as a `.md` file.
6. **External Scripts:** Consumer scripts (validators, batch processors) belong in `scripts/`, not in `app/`.
7. **Pull Request:** Submit a PR with a clear description of the changes.

## License

Distributed under the MIT License. See `LICENSE` for more information.
