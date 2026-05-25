from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.ui import templates

router = APIRouter()


def get_health_data():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": {
            "host": settings.APP_HOST,
            "port": settings.APP_PORT,
            "workers": settings.APP_WORKERS,
            "debug": settings.DEBUG,
        },
        "database": {
            "using_local_db": settings.USE_LOCAL_DB,
            "db_url": settings.DATABASE_URL,
        },
        "models": {
            "llm_model": settings.LLM_PROVIDER,
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
            "local_model": settings.LOCAL_MODEL if settings.USE_LOCAL_DB else None,
        },
        "rag_settings": {
            "chunking_strategy": settings.CHUNKING_STRATEGY,
            "batch_size": settings.BATCH_SIZE,
            "top_k": settings.TOP_K,
            "table_parsing_enabled": settings.ENABLE_TABLE_PARSING,
        },
        "vector_db": {
            "provider": "pgvector" if settings.USE_LOCAL_DB else "pinecone",
            "index_name": settings.PINECONE_INDEX_NAME
            if not settings.USE_LOCAL_DB
            else None,
            "cloud": settings.CLOUD if not settings.USE_LOCAL_DB else None,
            "region": settings.REGION if not settings.USE_LOCAL_DB else None,
        },
    }


@router.get("/", response_class=HTMLResponse, summary="UI Dashboard Shell")
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="pages/dashboard.html")


@router.get("/ui/health", response_class=HTMLResponse, summary="HTMX Health Partial")
def htmx_health_check(request: Request):
    data = get_health_data()
    return templates.TemplateResponse(
        request=request, name="partials/health_status.html", context={"data": data}
    )
