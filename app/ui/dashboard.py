from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.ui import templates

router = APIRouter()


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
