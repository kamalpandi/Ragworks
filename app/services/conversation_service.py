import uuid

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
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO conversations (id, tenant_id, thread_id, role, content) VALUES (%s, %s, %s, %s, %s)",
            [msg_id, tenant_id, thread_id, role, content],
        )


async def get_thread(
    tenant_id: str, thread_id: str, limit: int | None = None
) -> ConversationThread:
    limit = limit or settings.CONVERSATION_HISTORY_LENGTH
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
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


async def list_threads(tenant_id: str) -> list[dict]:
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """SELECT
                    thread_id,
                    (SELECT content FROM conversations c2
                     WHERE c2.thread_id = c.thread_id AND c2.role = 'user'
                     ORDER BY created_at ASC LIMIT 1) AS first_message,
                    COUNT(*) AS message_count,
                    MAX(created_at) AS last_updated
                FROM conversations c
                WHERE tenant_id = %s
                GROUP BY thread_id
                ORDER BY last_updated DESC""",
            [tenant_id],
        )
        rows = await cur.fetchall()
        return [
            {
                "thread_id": str(row["thread_id"]),
                "first_message": (
                    str(row["first_message"])[:60] + "..."
                    if row["first_message"] and len(str(row["first_message"])) > 60
                    else str(row["first_message"] or "")
                ),
                "message_count": row["message_count"],
                "last_updated": row["last_updated"].isoformat()
                if row["last_updated"]
                else "",
            }
            for row in rows
        ]


def create_thread_id() -> str:
    return str(uuid.uuid4())
