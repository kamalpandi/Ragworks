from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.models.log_entry import LogQuery
from app.ui import templates

router = APIRouter()


def _get_card_class(status: str) -> str:
    if status in ("connected", "running", "available"):
        return "var(--pico-ins-color)"
    if status in ("disconnected", "error", "unavailable"):
        return "var(--pico-del-color)"
    return "var(--pico-muted-color)"


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="pages/dashboard.html")


@router.get("/ui/dashboard/status", response_class=HTMLResponse)
async def htmx_status_cards(request: Request):
    from app.core.pool import get_pool

    db_status = "disconnected"
    try:
        pool = get_pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchone()
        db_status = "connected"
    except Exception:
        pass

    try:
        from app.core.pool import get_pool

        pool = get_pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM rag_vectors_" + str(settings.EMBEDDING_DIMENSION)
            )
            row = await cur.fetchone()
            doc_count = row[0] if row else 0
    except Exception:
        doc_count = 0

    try:
        pool = get_pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM api_keys")
            row = await cur.fetchone()
            key_count = row[0] if row else 0
    except Exception:
        key_count = 0

    vector_provider = "pgvector" if settings.USE_LOCAL_DB else "pinecone"

    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_status.html",
        context={
            "app_host": settings.APP_HOST,
            "app_port": settings.APP_PORT,
            "db_status": db_status,
            "db_status_color": _get_card_class(db_status),
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "doc_count": doc_count,
            "key_count": key_count,
            "vector_provider": vector_provider,
            "updated": datetime.now(UTC).strftime("%H:%M:%S"),
        },
    )


@router.get("/ui/dashboard/stats", response_class=HTMLResponse)
async def htmx_usage_stats(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev")
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0)

    query_count = 0
    ingest_count = 0
    total_tokens = 0
    chunks_created = 0

    try:
        from app.core.pool import get_pool

        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT operation, COUNT(*) as cnt, "
                    "COALESCE(SUM(tokens_prompt),0) + COALESCE(SUM(tokens_completion),0) AS tokens, "
                    "COALESCE(SUM(chunks_created),0) AS chunks "
                    "FROM usage_logs "
                    "WHERE tenant_id = %s AND created_at >= %s "
                    "GROUP BY operation",
                    [tenant_id, since],
                )
                for row in await cur.fetchall():
                    if row["operation"] == "query":
                        query_count = row["cnt"]
                        total_tokens += row["tokens"]
                    elif row["operation"] == "ingest":
                        ingest_count = row["cnt"]
                        chunks_created += row["chunks"]
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_stats.html",
        context={
            "query_count": query_count,
            "ingest_count": ingest_count,
            "total_tokens": total_tokens,
            "chunks_created": chunks_created,
            "chunking_strategy": settings.CHUNKING_STRATEGY,
            "top_k": settings.TOP_K,
            "retrieval_top_k": settings.RETRIEVAL_TOP_K,
            "reranker_enabled": settings.RERANKER_ENABLED,
            "reranker_provider": settings.RERANKER_PROVIDER,
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
            "system_prompt": settings.SYSTEM_PROMPT_FILE,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            "tenant_id": tenant_id,
        },
    )


@router.get("/ui/dashboard/activity", response_class=HTMLResponse)
async def htmx_recent_activity(request: Request):
    entries = []
    try:
        from app.observability.log_store import log_store

        q = LogQuery(limit=8, offset=0)
        entries = await log_store.query(q)
    except Exception:
        pass

    def _level_style(level: str) -> str:
        level = level.upper()
        if level in ("ERROR", "CRITICAL"):
            return "color: var(--pico-del-color); font-weight: bold;"
        if level == "WARNING":
            return "color: var(--pico-muted-color);"
        return "color: inherit;"

    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_activity.html",
        context={
            "entries": [
                {
                    "timestamp": e.timestamp[:19]
                    if len(e.timestamp) > 19
                    else e.timestamp,
                    "level": e.level,
                    "event": e.event,
                    "level_style": _level_style(e.level),
                }
                for e in entries
            ]
        },
    )


@router.get("/ui/dashboard/docs", response_class=HTMLResponse)
async def htmx_ingested_docs(request: Request):
    sources: list[str] = []
    try:
        from app.core.dependencies import get_db

        db = get_db()
        tenant_id = getattr(request.state, "tenant_id", "default")
        sources = await db.get_distinct_sources(tenant_id=tenant_id)
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_docs.html",
        context={"sources": sources, "count": len(sources)},
    )
