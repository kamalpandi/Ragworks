# How to Start the RAG Framework Server Locally

This guide covers running the RAG Framework on your local machine using
**PostgreSQL + PGVector** (Docker) and **OpenAI** as the LLM backend.

## Prerequisites

- **Python 3.12+** — [pyenv](https://github.com/pyenv/pyenv) or [python.org](https://python.org)
- **Docker** — [Docker Desktop](https://docker.com) (for PGVector database)
- **OpenAI API Key** — [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **uv** — `pip install uv` or `brew install uv`

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> rag-framework && cd rag-framework
uv venv && source .venv/bin/activate && uv sync

# 2. Configure
cp .env.example .env
# Edit .env: set OPENAI_API_KEY=sk-your-key-here

# 3. Start the database
docker run -d \
  --name rag-postgres \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=rag_db \
  -p 5432:5432 \
  -v rag_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

# 4. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

Server is now running at **http://localhost:8000**.

---

## Step-by-Step

### 1. Clone and Install Dependencies

```bash
git clone <repo-url> rag-framework
cd rag-framework

uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
```

### 2. Configure Environment

Copy the example config and set your API key:

```bash
cp .env.example .env
```

Edit `.env` — the only required change is your OpenAI key:

```ini
OPENAI_API_KEY=sk-your-key-here

# Optional: skip API key auth during development
DEV_API_KEY=dev-skip-auth
```

Default settings work out of the box:
- Database: `postgresql://user:password@localhost:5432/rag_db`
- LLM: `openai` with `gpt-4o-mini`
- Chunking: `recursive`
- Auth: enabled (exempt on `/health`, `/docs`, `/metrics`, `/login`)
- Rate limiting: 60 queries/min, 10 ingests/min

See `.env.example` for all configurable options.

### 3. Start PostgreSQL with PGVector

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

Verify the database is ready:

```bash
docker ps | grep rag-postgres
# Should show: pgvector/pgvector:pg16   Up X seconds
```

> To stop: `docker stop rag-postgres`. To restart: `docker start rag-postgres`.
> To remove completely: `docker rm -f rag-postgres && docker volume rm rag_data`.

### 4. Start the Server

**Development (hot reload):**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Production-like (single process):**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

The server initializes in this order:
1. OpenTelemetry tracing
2. Structured logging (structlog)
3. Connection pool to PostgreSQL (retries up to 10 times if DB isn't ready)
4. Database migrations (creates tables if missing: `api_keys`, `conversations`, `usage_logs`, `rag_logs`)
5. Log store background drain (writes structured logs to PostgreSQL)

### 5. Verify It Works

**With dev key (recommended for development):**

```bash
# Health check (exempt from auth — no key needed)
curl http://localhost:8000/health
# → {"status":"healthy","database":"connected"}

# API calls with the dev key
curl -H "X-API-Key: dev-skip-auth" http://localhost:8000/api/v1/config

# Swagger UI (exempt from auth)
open http://localhost:8000/docs

# Web UI (exempt from auth)
open http://localhost:8000/
```

---

## Verification

### Smoke test the full pipeline

```bash
# Set your dev key (add to ~/.zshrc for persistence)
export DEV_KEY="dev-skip-auth"

# 1. Ingest a URL
curl -X POST "http://localhost:8000/api/v1/ingest/url" \
  -H "X-API-Key: $DEV_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}'

# 2. List ingested files
curl -H "X-API-Key: $DEV_KEY" \
  "http://localhost:8000/api/v1/ingest/files"

# 3. Query the knowledge base
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: $DEV_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is RAG?", "file_name": "Retrieval-augmented_generation"}'
```

### Web UI pages

| Page          | URL                         |
|---------------|-----------------------------|
| Dashboard     | http://localhost:8000/      |
| Query Chat    | http://localhost:8000/query |
| Ingest        | http://localhost:8000/ingest|
| Config        | http://localhost:8000/config|
| Prompts       | http://localhost:8000/prompts|
| API Docs      | http://localhost:8000/docs  |

---

## Troubleshooting

### "Port 5432 is already in use"

PostgreSQL or another service is using that port:

```bash
# Find what's using it
lsof -i :5432

# If it's an old rag-postgres container:
docker rm -f rag-postgres && docker run -d --name rag-postgres ...
```

### "Port 8000 is already in use"

```bash
# Kill the old uvicorn process
lsof -ti :8000 | xargs kill

# Or use a different port
uvicorn main:app --port 8001
```

### "Database connection refused"

The server retries up to 10 times at startup (with 2–30 second delays). If all retries fail, check:

```bash
# Is Docker running?
docker ps

# Is the container started?
docker start rag-postgres

# Are the credentials correct?
# Default: postgresql://user:password@localhost:5432/rag_db
# Match these to the values in your docker run command
```

### "Missing OPENAI_API_KEY"

```bash
# Check your .env file
grep OPENAI .env

# Ensure the value is set and not empty
# OPENAI_API_KEY=sk-xxx  (not OPENAI_API_KEY=)
```

### Server starts but /health returns "degraded"

The app is running but the database is unreachable. Verify the PGVector container is healthy:

```bash
docker exec rag-postgres pg_isready -U user -d rag_db
# Should return: /var/run/postgresql:5432 - accepting connections
```

### "models/ directory not found" warning

This is harmless when using OpenAI as your LLM provider. It only matters if you switch to `LLM_PROVIDER=llamacpp`. To suppress it:

```bash
mkdir -p models
```

---

## Next Steps

- **Run demo scripts:** `python scripts/demo_full_pipeline.py` (requires server running)
- **Try query strategies:** Add `"translation_strategy": "hyde"` or `"multi_query"` to query requests
- **Switch system prompts:** Set `SYSTEM_PROMPT_FILE=strict_context_only` in `.env`
- **Ingest a PDF:** `curl -X POST .../api/v1/ingest/file -F "file=@document.pdf"`
- **Production deployment:** See `deploy/rag-framework.service` for a systemd unit file

---

## Switching LLM Providers

| Provider   | `.env` setting           | Requirements                |
|------------|--------------------------|-----------------------------|
| OpenAI     | `LLM_PROVIDER=openai`    | `OPENAI_API_KEY`            |
| DeepSeek   | `LLM_PROVIDER=deepseek`  | `DEEPSEEK_API_KEY`          |
| Ollama     | `LLM_PROVIDER=ollama`    | `ollama serve` on localhost |
| llama.cpp  | `LLM_PROVIDER=llamacpp`  | GGUF file in `models/` dir  |

Restart the server after changing `LLM_PROVIDER`.

## Switching Databases

| Database   | `.env` setting           | Requirements                |
|------------|--------------------------|-----------------------------|
| PGVector   | `USE_LOCAL_DB=true`      | Docker `pgvector/pgvector`  |
| Pinecone   | `USE_LOCAL_DB=false`     | `PINECONE_API_KEY`          |

Restart the server after changing `USE_LOCAL_DB`.
