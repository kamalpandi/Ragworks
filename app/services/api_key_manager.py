import hashlib
import secrets
import uuid

from psycopg.rows import dict_row

from app.core.pool import get_pool
from app.observability.logger import get_logger

logger = get_logger(__name__)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_raw_key() -> str:
    return f"rag-{secrets.token_urlsafe(32)}"


async def create_api_key(tenant_id: str, label: str = "") -> tuple[str, str]:
    raw_key = generate_raw_key()
    key_hash = _hash_key(raw_key)
    key_id = str(uuid.uuid4())

    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO api_keys (id, key_hash, tenant_id, label) VALUES (%s, %s, %s, %s)",
            [key_id, key_hash, tenant_id, label],
        )

    logger.info("api_key_created", tenant_id=tenant_id, key_id=key_id)
    return raw_key, key_id


async def validate_api_key(key: str) -> tuple[str, str] | None:
    key_hash = _hash_key(key)
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT tenant_id, id FROM api_keys WHERE key_hash = %s AND is_active = TRUE",
            [key_hash],
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return row["tenant_id"], str(row["id"])


async def deactivate_api_key(key_id: str) -> bool:
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "UPDATE api_keys SET is_active = FALSE WHERE id = %s RETURNING id",
            [key_id],
        )
        row = await cur.fetchone()
        return row is not None
