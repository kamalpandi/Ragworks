import json
from typing import Any, Dict, List, Optional

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Literal

from app.core.config import settings
from app.core.interfaces import BaseVectorDB
from app.core.pool import get_pool, get_sync_connection
from app.models.domain import DocumentChunk
from app.observability.logger import get_logger

logger = get_logger(__name__)


class PGVectorDB(BaseVectorDB):
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.table_name = f"rag_vectors_{self.dimension}"
        self._init_db()

    def _init_db(self):
        """Sync init — only runs once at startup, fine to be blocking."""
        with get_sync_connection() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            conn.execute(
                SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    tenant_id TEXT DEFAULT 'default',
                    metadata JSONB,
                    embedding vector
                )
            """).format(table=Identifier(self.table_name))
            )
            conn.execute(
                SQL("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = {table_name_literal} AND column_name = 'tenant_id'
                    ) THEN
                        ALTER TABLE {table} ADD COLUMN tenant_id TEXT DEFAULT 'default';
                    END IF;
                END $$;
            """).format(
                    table_name_literal=Literal(self.table_name),
                    table=Identifier(self.table_name),
                )
            )
            conn.execute(
                SQL("""
                CREATE INDEX IF NOT EXISTS {idx_name}
                ON {table} USING hnsw (embedding vector_cosine_ops)
            """).format(
                    idx_name=Identifier(f"{self.table_name}_embedding_idx"),
                    table=Identifier(self.table_name),
                )
            )

    async def upsert(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        tenant_id: str = "default",
    ):
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match!")

        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                data = [
                    (
                        chunk.id,
                        chunk.text,
                        chunk.metadata.get("tenant_id", "default"),
                        json.dumps(chunk.metadata),
                        embedding,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]
                await cur.executemany(
                    SQL("""
                        INSERT INTO {table} (id, text, tenant_id, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET text = EXCLUDED.text,
                            tenant_id = EXCLUDED.tenant_id,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """).format(table=Identifier(self.table_name)),
                    data,
                )

    async def get_distinct_sources(self, tenant_id: str = "default") -> List[str]:
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    SQL(
                        "SELECT DISTINCT metadata->>'source' AS source FROM {table} WHERE tenant_id = %s ORDER BY source"
                    ).format(table=Identifier(self.table_name)),
                    [tenant_id],
                )
                rows = await cur.fetchall()
                return [str(row["source"]) for row in rows if row.get("source")]

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
    ) -> List[DocumentChunk]:
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if filters and "source" in filters:
                    source_file = filters["source"].get("$eq")
                    if source_file:
                        final_query = SQL("""
                            SELECT id, text, metadata, 1 - (embedding <=> %s::vector) AS score
                            FROM {table}
                            WHERE tenant_id = %s AND metadata->>'source' = %s
                            ORDER BY embedding <=> %s::vector
                            LIMIT %s
                        """).format(table=Identifier(self.table_name))
                        params = [
                            query_vector,
                            tenant_id,
                            source_file,
                            query_vector,
                            top_k,
                        ]
                        await cur.execute(final_query, params)
                        rows = await cur.fetchall()
                        return [
                            DocumentChunk(
                                id=str(row["id"]),
                                text=str(row["text"]),
                                metadata=row["metadata"],
                                score=float(row["score"]),
                            )
                            for row in rows
                        ]

                final_query = SQL("""
                    SELECT id, text, metadata, 1 - (embedding <=> %s::vector) AS score
                    FROM {table}
                    WHERE tenant_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """).format(table=Identifier(self.table_name))
                params = [query_vector, tenant_id, query_vector, top_k]
                await cur.execute(final_query, params)
                rows = await cur.fetchall()

                return [
                    DocumentChunk(
                        id=str(row["id"]),
                        text=str(row["text"]),
                        metadata=row["metadata"],
                        score=float(row["score"]),
                    )
                    for row in rows
                ]
