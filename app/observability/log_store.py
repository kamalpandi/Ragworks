import asyncio
import json
import logging
from typing import Any, Dict, List

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier

from app.core.config import settings
from app.models.log_entry import LogEntry, LogQuery

_sys_logger = logging.getLogger("rag_framework.log_store")


class LogStore:
    """Database-backed structured log storage.

    Uses asyncio.Queue for enqueue from structlog processors (sync context)
    and async drain via background task.
    """

    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.table_name = "rag_logs"
        self._enabled = settings.OBSERVABILITY_ENABLED
        self._table_ready = False
        self._write_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=10000)
        self._drain_task: asyncio.Task[Any] | None = None
        self._shutdown = False

    def _get_sync_connection(self):
        return psycopg.connect(self.db_url, autocommit=True)

    async def _get_async_connection(self):
        conn = await psycopg.AsyncConnection.connect(
            self.db_url,
            row_factory=dict_row,
            autocommit=True,
        )
        return conn

    def _ensure_table(self):
        if self._table_ready or not self._enabled:
            return
        try:
            with self._get_sync_connection() as conn:
                conn.execute(
                    SQL(
                        """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        level TEXT NOT NULL,
                        logger_name TEXT,
                        event TEXT NOT NULL,
                        trace_id TEXT,
                        request_id TEXT,
                        message TEXT,
                        extra JSONB DEFAULT '{{}}'::jsonb
                    )
                """
                    ).format(table=Identifier(self.table_name))
                )
                conn.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS {idx} ON {table} (timestamp DESC)"
                    ).format(
                        idx=Identifier(f"{self.table_name}_ts_idx"),
                        table=Identifier(self.table_name),
                    )
                )
                conn.execute(
                    SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (level)").format(
                        idx=Identifier(f"{self.table_name}_level_idx"),
                        table=Identifier(self.table_name),
                    )
                )
                conn.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS {idx} ON {table} (trace_id)"
                    ).format(
                        idx=Identifier(f"{self.table_name}_trace_idx"),
                        table=Identifier(self.table_name),
                    )
                )
            self._table_ready = True
            _sys_logger.info("log_store_table_ready table=%s", self.table_name)
        except Exception as e:
            _sys_logger.warning("log_store_table_init_failed: %s", e)
            self._enabled = False

    def enqueue(self, entry: Dict[str, Any]):
        """Called from structlog processor (sync context). Thread-safe with asyncio.Queue."""
        if not self._enabled:
            return
        try:
            self._write_queue.put_nowait(entry)
        except asyncio.QueueFull:
            _sys_logger.warning("log_store_queue_full_dropping")

    async def start(self):
        if not self._enabled:
            return
        self._ensure_table()
        if not self._enabled:
            return
        self._shutdown = False
        self._drain_task = asyncio.create_task(self._drain_loop())
        _sys_logger.info("log_store_drain_started")

    async def stop(self):
        self._shutdown = True
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        await self._flush_remaining()

    async def _drain_loop(self):
        batch: List[Dict[str, Any]] = []
        while not self._shutdown:
            try:
                # Wait for first item with timeout
                try:
                    item = await asyncio.wait_for(self._write_queue.get(), timeout=0.5)
                    batch.append(item)
                except asyncio.TimeoutError:
                    pass

                # Drain remaining without blocking
                while len(batch) < 50:
                    try:
                        item = self._write_queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break

                if batch:
                    await self._write_batch(batch)
                    batch.clear()
            except Exception as e:
                _sys_logger.warning("log_store_drain_error: %s", e)
                await asyncio.sleep(1)

    async def _flush_remaining(self):
        batch: List[Dict[str, Any]] = []
        while True:
            try:
                batch.append(self._write_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            await self._write_batch(batch)

    async def _write_batch(self, batch: List[Dict[str, Any]]):
        if not self._enabled:
            return
        try:
            async with await self._get_async_connection() as conn:
                async with conn.cursor() as cur:
                    data = [
                        (
                            e["id"],
                            e["timestamp"],
                            e["level"],
                            e["logger_name"],
                            e["event"],
                            e.get("trace_id"),
                            e.get("request_id"),
                            e["message"],
                            json.dumps(e.get("extra", {})),
                        )
                        for e in batch
                    ]
                    await cur.executemany(
                        SQL(
                            """INSERT INTO {table}
                            (id, timestamp, level, logger_name, event, trace_id, request_id, message, extra)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """
                        ).format(table=Identifier(self.table_name)),
                        data,
                    )
        except Exception as e:
            _sys_logger.warning("log_store_batch_write_failed: %s", e)

    async def query(self, q: LogQuery) -> List[LogEntry]:
        if not self._enabled:
            return []

        conditions = []
        params: List[Any] = []

        if q.level:
            conditions.append(SQL("level = %s"))
            params.append(q.level.upper())
        if q.logger_name:
            conditions.append(SQL("logger_name = %s"))
            params.append(q.logger_name)
        if q.event:
            conditions.append(SQL("event = %s"))
            params.append(q.event)
        if q.trace_id:
            conditions.append(SQL("trace_id = %s"))
            params.append(q.trace_id)
        if q.request_id:
            conditions.append(SQL("request_id = %s"))
            params.append(q.request_id)
        if q.since:
            conditions.append(SQL("timestamp >= %s"))
            params.append(q.since)
        if q.until:
            conditions.append(SQL("timestamp <= %s"))
            params.append(q.until)
        if q.search:
            conditions.append(SQL("(message ILIKE %s OR event ILIKE %s)"))
            search_pattern = f"%{q.search}%"
            params.extend([search_pattern, search_pattern])

        where_clause = SQL("")
        if conditions:
            where_clause = SQL("WHERE ") + SQL(" AND ").join(conditions)

        query_sql = SQL(
            "SELECT * FROM {table} {where} ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        ).format(table=Identifier(self.table_name), where=where_clause)

        params.extend([q.limit, q.offset])

        try:
            async with await self._get_async_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query_sql, params)
                    rows = await cur.fetchall()
                    return [
                        LogEntry(
                            id=row["id"],
                            timestamp=row["timestamp"].isoformat(),
                            level=row["level"],
                            logger_name=row["logger_name"] or "",
                            event=row["event"],
                            trace_id=row.get("trace_id"),
                            request_id=row.get("request_id"),
                            message=row["message"] or "",
                            extra=(
                                row["extra"] if isinstance(row["extra"], dict) else {}
                            ),
                        )
                        for row in rows
                    ]
        except Exception as e:
            _sys_logger.warning("log_store_query_failed: %s", e)
            return []

    async def count(self, q: LogQuery) -> int:
        if not self._enabled:
            return 0
        conditions = []
        params: List[Any] = []
        if q.level:
            conditions.append(SQL("level = %s"))
            params.append(q.level.upper())
        if q.trace_id:
            conditions.append(SQL("trace_id = %s"))
            params.append(q.trace_id)
        if q.search:
            conditions.append(SQL("(message ILIKE %s OR event ILIKE %s)"))
            search_pattern = f"%{q.search}%"
            params.extend([search_pattern, search_pattern])

        where_clause = SQL("")
        if conditions:
            where_clause = SQL("WHERE ") + SQL(" AND ").join(conditions)

        try:
            async with await self._get_async_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        SQL("SELECT COUNT(*) as cnt FROM {table} {where}").format(
                            table=Identifier(self.table_name),
                            where=where_clause,
                        ),
                        params,
                    )
                    row = await cur.fetchone()
                    return row["cnt"] if row else 0
        except Exception:
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        if not self._enabled:
            return {"enabled": False}

        try:
            async with await self._get_async_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        SQL(
                            "SELECT level, COUNT(*) as cnt FROM {table} GROUP BY level ORDER BY cnt DESC"
                        ).format(table=Identifier(self.table_name))
                    )
                    level_counts = {
                        row["level"]: row["cnt"] for row in await cur.fetchall()
                    }

                    await cur.execute(
                        SQL("SELECT COUNT(*) as cnt FROM {table}").format(
                            table=Identifier(self.table_name)
                        )
                    )
                    total = (await cur.fetchone())["cnt"]

            return {
                "enabled": True,
                "total_entries": total,
                "levels": level_counts,
            }
        except Exception as e:
            _sys_logger.warning("log_store_stats_failed: %s", e)
            return {"enabled": True, "total_entries": 0, "levels": {}}


log_store = LogStore()
