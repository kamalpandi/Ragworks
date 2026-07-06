from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    config,
    conversations,
    eval as eval_endpoints,
    ingest,
    list_prompts,
    logs,
    query,
    usage,
)

api_router = APIRouter()

api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(query.router, prefix="/query", tags=["Retrieval"])
api_router.include_router(config.router, prefix="/config", tags=["Configuration"])
api_router.include_router(
    list_prompts.router,
    prefix="/prompts",
    tags=["List all System and user prompts from folder"],
)
api_router.include_router(eval_endpoints.router, prefix="/eval", tags=["Evaluation"])
api_router.include_router(logs.router, prefix="/logs", tags=["Observability"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)
api_router.include_router(usage.router, prefix="/usage", tags=["Usage"])
