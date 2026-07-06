import uuid
from typing import List

from psycopg.rows import dict_row

from app.core.config import settings
from app.core.pool import get_pool
from app.models.conversation import ConversationMessage, ConversationThread
from app.observability.logger import get_logger

logger = get_logger(__name__)


async def store_message(
    tenant_id: str, thread_id: str, role: str, content: str
) -> None:
    pool = get_pool()
    msg_id = str(uuid.uuid4())
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO conversations (id, tenant_id, thread_id, role, content) VALUES (%s, %s, %s, %s, %s)",
                [msg_id, tenant_id, thread_id, role, content],
            )


async def get_thread(
    tenant_id: str, thread_id: str, limit: int | None = None
) -> ConversationThread:
    limit = limit or settings.CONVERSATION_HISTORY_LENGTH
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_id, thread_id, role, content, created_at "
                "FROM conversations "
                "WHERE tenant_id = %s AND thread_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                [tenant_id, thread_id, limit],
            )
            rows = await cur.fetchall()
            messages = [
                ConversationMessage(
                    id=str(row["id"]),
                    tenant_id=str(row["tenant_id"]),
                    thread_id=str(row["thread_id"]),
                    role=str(row["role"]),
                    content=str(row["content"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]
            messages.reverse()
            return ConversationThread(
                thread_id=thread_id, tenant_id=tenant_id, messages=messages
            )


async def list_threads(tenant_id: str) -> List[str]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT DISTINCT thread_id FROM conversations WHERE tenant_id = %s ORDER BY thread_id",
                [tenant_id],
            )
            rows = await cur.fetchall()
            return [str(row["thread_id"]) for row in rows]


def create_thread_id() -> str:
    return str(uuid.uuid4())
