from app.core.pool import get_sync_connection
from app.observability.logger import get_logger

logger = get_logger(__name__)


def run_migrations():
    with get_sync_connection() as conn:
        _create_api_keys_table(conn)
        _create_conversations_table(conn)
        _create_usage_logs_table(conn)
    logger.info("migrations_complete")


def _create_api_keys_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key_hash TEXT UNIQUE NOT NULL,
            tenant_id TEXT NOT NULL,
            label TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    logger.info("table_created", table="api_keys")


def _create_conversations_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_tenant_thread_time
        ON conversations (tenant_id, thread_id, created_at)
    """)
    logger.info("table_created", table="conversations")


def _create_usage_logs_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            tokens_prompt INT DEFAULT 0,
            tokens_completion INT DEFAULT 0,
            chunks_created INT DEFAULT 0,
            chunks_retrieved INT DEFAULT 0,
            source_name TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_logs_tenant_time
        ON usage_logs (tenant_id, created_at DESC)
    """)
    logger.info("table_created", table="usage_logs")
