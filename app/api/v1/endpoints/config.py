from fastapi import APIRouter, Request

from app.core.config import settings
from app.models.frontend_config import FrontendConfig

router = APIRouter()


@router.get("", summary="Get frontend configuration")
async def get_frontend_config(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default")
    return {
        "tenant_id": tenant_id,
        "config": FrontendConfig(
            APP_HOST=settings.APP_HOST,
            APP_PORT=settings.APP_PORT,
            DEBUG=settings.DEBUG,
            USE_LOCAL_DB=settings.USE_LOCAL_DB,
            LLM_PROVIDER=settings.LLM_PROVIDER,
            LOCAL_MODEL=settings.LOCAL_MODEL,
            AVAILABLE_LOCAL_MODELS=settings.AVAILABLE_LOCAL_MODELS,
            LLM_MODEL=settings.LLM_MODEL,
            OLLAMA_MODEL=settings.OLLAMA_MODEL,
            REMOTE_LLAMACPP_URL=settings.REMOTE_LLAMACPP_URL,
            OLLAMA_BASE_URL=settings.OLLAMA_BASE_URL,
            LLM_TEMP=settings.LLM_TEMP,
            LLM_MAX_TOKENS=settings.LLM_MAX_TOKENS,
            LLM_N_CTX=settings.LLM_N_CTX,
            LLM_STOP_SEQUENCES=settings.LLM_STOP_SEQUENCES,
            EMBEDDING_MODEL=settings.EMBEDDING_MODEL,
            EMBEDDING_DIMENSION=settings.EMBEDDING_DIMENSION,
            EMBEDDING_MODEL_MAX_TOKEN=settings.EMBEDDING_MODEL_MAX_TOKEN,
            SYSTEM_PROMPT_FILE=settings.SYSTEM_PROMPT_FILE,
            CHUNKING_STRATEGY=settings.CHUNKING_STRATEGY,
            ENABLE_TABLE_PARSING=settings.ENABLE_TABLE_PARSING,
            TOP_K=settings.TOP_K,
            RETRIEVAL_TOP_K=settings.RETRIEVAL_TOP_K,
            INDEX_NAME=settings.PINECONE_INDEX_NAME,
            CLOUD=settings.CLOUD,
            REGION=settings.REGION,
            BATCH_SIZE=settings.BATCH_SIZE,
            RERANKER_ENABLED=settings.RERANKER_ENABLED,
            RERANKER_PROVIDER=settings.RERANKER_PROVIDER,
            RERANK_TOP_K=settings.RERANK_TOP_K,
            RATE_LIMIT_ENABLED=settings.RATE_LIMIT_ENABLED,
            OBSERVABILITY_ENABLED=settings.OBSERVABILITY_ENABLED,
            LOG_LEVEL=settings.LOG_LEVEL,
            LOG_FORMAT=settings.LOG_FORMAT,
            OTEL_EXPORTER_TYPE=settings.OTEL_EXPORTER_TYPE,
            EVAL_ENABLED=settings.EVAL_ENABLED,
            EVAL_METRICS=settings.EVAL_METRICS,
            EVAL_RESULTS_DIR=settings.EVAL_RESULTS_DIR,
        ),
    }
