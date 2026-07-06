from typing import Dict, Any, cast

from psycopg import Connection
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)

_pool: AsyncConnectionPool | None = None


async def init_pool():
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=settings.DB_POOL_MIN_SIZE,
        max_size=settings.DB_POOL_MAX_SIZE,
        timeout=settings.DB_POOL_TIMEOUT,
    )
    await _pool.open()
    logger.info(
        "pool_initialized", min=settings.DB_POOL_MIN_SIZE, max=settings.DB_POOL_MAX_SIZE
    )


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("pool_closed")


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "Connection pool not initialized. Call init_pool() at startup."
        )
    return _pool


def get_sync_connection() -> Connection[Dict[str, Any]]:
    from psycopg.rows import dict_row

    conn = Connection.connect(
        settings.DATABASE_URL,
        row_factory=dict_row,
        autocommit=True,
    )
    return cast(Connection[Dict[str, Any]], conn)
