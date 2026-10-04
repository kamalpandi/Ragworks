"""Dashboard fragment views.

Each fragment fetches its data from the JSON API via ``api_client`` and
renders a partial. No backend imports.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

router = APIRouter()


def _db_status_color(status: str) -> str:
    if status in ("connected", "running", "available"):
        return "var(--pico-ins-color)"
    if status in ("disconnected", "error", "unavailable"):
        return "var(--pico-del-color)"
    return "var(--pico-muted-color)"


def _level_style(level: str) -> str:
    level = level.upper()
    if level in ("ERROR", "CRITICAL"):
        return "color: var(--pico-del-color); font-weight: bold;"
    if level == "WARNING":
        return "color: var(--pico-muted-color);"
    return "color: inherit;"


@router.get("/ui/dashboard/status")
async def dashboard_status(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    key = session.api_key
    status = (await client.get("/api/v1/status", api_key=key)).json()
    config = (await client.get("/api/v1/config", api_key=key)).json()["config"]
    db_status = status["database"]
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_status.html",
        context={
            "app_host": config["APP_HOST"],
            "app_port": config["APP_PORT"],
            "db_status": db_status,
            "db_status_color": _db_status_color(db_status),
            "llm_provider": config["LLM_PROVIDER"],
            "llm_model": config["LLM_MODEL"],
            "doc_count": status["documents"],
            "key_count": status["api_keys"],
            "vector_provider": status["vector_provider"],
            "updated": datetime.now(UTC).strftime("%H:%M:%S"),
        },
    )


@router.get("/ui/dashboard/activity")
async def dashboard_activity(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    data = (
        await client.get("/api/v1/logs/", api_key=session.api_key, params={"limit": 8})
    ).json()
    entries = [
        {
            "timestamp": e["timestamp"],
            "level": e["level"],
            "event": e["event"],
            "level_style": _level_style(e["level"]),
        }
        for e in data["entries"]
    ]
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_activity.html",
        context={"entries": entries},
    )


@router.get("/ui/dashboard/docs")
async def dashboard_docs(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    data = (await client.get("/api/v1/ingest/files", api_key=session.api_key)).json()
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_docs.html",
        context={"sources": data["sources"], "count": data["count"]},
    )


@router.get("/ui/dashboard/stats")
async def dashboard_stats(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    key = session.api_key
    dash = (await client.get("/api/v1/dashboard", api_key=key)).json()
    cfg = (await client.get("/api/v1/config", api_key=key)).json()
    stats = dash["stats"]
    config = cfg["config"]
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_stats.html",
        context={
            "query_count": stats["query_count"],
            "ingest_count": stats["ingest_count"],
            "total_tokens": stats["total_tokens"],
            "chunks_created": stats["chunks_created"],
            "chunking_strategy": config["CHUNKING_STRATEGY"],
            "top_k": config["TOP_K"],
            "retrieval_top_k": config["RETRIEVAL_TOP_K"],
            "reranker_enabled": config["RERANKER_ENABLED"],
            "reranker_provider": config["RERANKER_PROVIDER"],
            "embedding_model": config["EMBEDDING_MODEL"],
            "embedding_dimension": config["EMBEDDING_DIMENSION"],
            "system_prompt": config["SYSTEM_PROMPT_FILE"],
            "rate_limit_enabled": config["RATE_LIMIT_ENABLED"],
            "tenant_id": cfg["tenant_id"],
        },
    )
