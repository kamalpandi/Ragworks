from app.core.pool import get_pool
from app.observability.logger import get_logger
from app.observability.metrics import rag_usage_queries_total, rag_usage_tokens_total

logger = get_logger(__name__)


async def track_query(
    tenant_id: str, tokens_prompt: int, tokens_completion: int, chunks_retrieved: int
):
    pool = get_pool()
    try:
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO usage_logs (tenant_id, operation, tokens_prompt, tokens_completion, chunks_retrieved) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    tenant_id,
                    "query",
                    tokens_prompt,
                    tokens_completion,
                    chunks_retrieved,
                ],
            )
        rag_usage_queries_total.labels(tenant_id=tenant_id).inc()
        rag_usage_tokens_total.labels(tenant_id=tenant_id, type="prompt").inc(
            tokens_prompt
        )
        rag_usage_tokens_total.labels(tenant_id=tenant_id, type="completion").inc(
            tokens_completion
        )
    except Exception:
        logger.warning("usage_track_failed", operation="query", tenant_id=tenant_id)


async def track_ingest(tenant_id: str, chunks_created: int, source_name: str):
    pool = get_pool()
    try:
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO usage_logs (tenant_id, operation, chunks_created, source_name) "
                "VALUES (%s, %s, %s, %s)",
                [tenant_id, "ingest", chunks_created, source_name],
            )
    except Exception:
        logger.warning("usage_track_failed", operation="ingest", tenant_id=tenant_id)
