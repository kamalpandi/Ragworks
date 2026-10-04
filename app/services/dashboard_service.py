"""Dashboard read models.

Composes status, usage statistics, recent activity, and ingested documents
from existing infrastructure. The frontend consumes this through the JSON
API; the UI layer no longer touches the database directly.
"""

from datetime import UTC, datetime

from psycopg import Error as PsycopgError
from psycopg.rows import dict_row

from app.core.config import settings
from app.core.pool import get_pool

# Resilience boundary only: infrastructure failures degrade to zero-stats so the
# dashboard still renders. Programming errors (TypeError, AttributeError,
# KeyError) are intentionally NOT caught — they indicate bugs and must surface as
# 500s rather than be silently swallowed into empty statistics.
_DB_ERRORS = (PsycopgError, OSError, RuntimeError)


async def get_status() -> dict:
    db_status = "disconnected"
    doc_count = 0
    key_count = 0

    try:
        pool = get_pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchone()
        db_status = "connected"
    except _DB_ERRORS:
        return {
            "database": db_status,
            "documents": doc_count,
            "api_keys": key_count,
            "vector_provider": _vector_provider(),
        }

    try:
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM rag_vectors_" + str(settings.EMBEDDING_DIMENSION)
            )
            row = await cur.fetchone()
            doc_count = row[0] if row else 0
    except _DB_ERRORS:
        doc_count = 0

    try:
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM api_keys")
            row = await cur.fetchone()
            key_count = row[0] if row else 0
    except _DB_ERRORS:
        key_count = 0

    return {
        "database": db_status,
        "documents": doc_count,
        "api_keys": key_count,
        "vector_provider": _vector_provider(),
    }


async def get_usage_stats(tenant_id: str, since: datetime | None = None) -> dict:
    since = since or datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    stats = {
        "query_count": 0,
        "ingest_count": 0,
        "total_tokens": 0,
        "chunks_created": 0,
    }

    try:
        pool = get_pool()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT operation, COUNT(*) AS cnt, "
                "COALESCE(SUM(tokens_prompt),0) + COALESCE(SUM(tokens_completion),0) AS tokens, "
                "COALESCE(SUM(chunks_created),0) AS chunks "
                "FROM usage_logs "
                "WHERE tenant_id = %s AND created_at >= %s "
                "GROUP BY operation",
                [tenant_id, since],
            )
            for row in await cur.fetchall():
                if row["operation"] == "query":
                    stats["query_count"] = row["cnt"]
                    stats["total_tokens"] += row["tokens"]
                elif row["operation"] == "ingest":
                    stats["ingest_count"] = row["cnt"]
                    stats["chunks_created"] += row["chunks"]
    except _DB_ERRORS:
        pass

    return stats


async def get_recent_activity(limit: int = 8) -> list[dict]:
    from app.models.log_entry import LogQuery
    from app.observability.log_store import log_store

    try:
        entries = await log_store.query(LogQuery(limit=limit, offset=0))
    except _DB_ERRORS:
        return []

    activity = []
    for e in entries:
        timestamp = e.timestamp[:19] if len(e.timestamp) > 19 else e.timestamp
        activity.append({"timestamp": timestamp, "level": e.level, "event": e.event})
    return activity


async def get_ingested_docs(tenant_id: str) -> list[str]:
    from app.core.dependencies import get_db

    try:
        db = get_db()
        return await db.get_distinct_sources(tenant_id=tenant_id)
    except _DB_ERRORS:
        return []


async def get_dashboard(tenant_id: str) -> dict:
    return {
        "status": await get_status(),
        "stats": await get_usage_stats(tenant_id),
        "activity": await get_recent_activity(),
        "docs": await get_ingested_docs(tenant_id),
    }


def _vector_provider() -> str:
    return "pgvector" if settings.USE_LOCAL_DB else "pinecone"
