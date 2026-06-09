import json
from typing import Any, Dict, List, Optional, cast

import psycopg
import psycopg.rows
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier

from app.core.config import settings
from app.core.interfaces import BaseVectorDB
from app.models.domain import DocumentChunk


class PGVectorDB(BaseVectorDB):
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.table_name = f"rag_vectors_{self.dimension}"
        print(f"rag_vectors_{self.dimension}")
        self._init_db()

    def _get_sync_connection(self) -> psycopg.Connection[Dict[str, Any]]:
        conn = psycopg.connect(
            self.db_url,
            row_factory=dict_row,  # type: ignore[bad-argument-type]
            autocommit=True,
        )
        return cast(psycopg.Connection[Dict[str, Any]], conn)

    async def _get_async_connection(self) -> psycopg.AsyncConnection[Dict[str, Any]]:
        conn = await psycopg.AsyncConnection.connect(
            self.db_url,
            row_factory=psycopg.rows.dict_row,  # type: ignore[bad-argument-type]
            autocommit=True,
        )
        return cast(psycopg.AsyncConnection[Dict[str, Any]], conn)

    def _init_db(self):
        """Sync init — only runs once at startup, fine to be blocking."""
        with psycopg.connect(self.db_url, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            conn.execute(
                SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    metadata JSONB,
                    embedding vector
                )
            """).format(table=Identifier(self.table_name))
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

    async def upsert(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match!")

        async with await self._get_async_connection() as conn:
            async with conn.cursor() as cur:
                data = [
                    (chunk.id, chunk.text, json.dumps(chunk.metadata), embedding)
                    for chunk, embedding in zip(chunks, embeddings)
                ]
                await cur.executemany(
                    SQL("""
                        INSERT INTO {table} (id, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """).format(table=Identifier(self.table_name)),
                    data,
                )

    async def get_distinct_sources(self) -> List[str]:
        async with await self._get_async_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SQL(
                        "SELECT DISTINCT metadata->>'source' AS source FROM {table} ORDER BY source"
                    ).format(table=Identifier(self.table_name))
                )
                rows = await cur.fetchall()
                return [str(row["source"]) for row in rows if row.get("source")]

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        if not filters or "source" not in filters:
            return []

        source_file = filters["source"].get("$eq")
        if not source_file:
            return []

        final_query = SQL("""
            SELECT id, text, metadata, 1 - (embedding <=> %s::vector) AS score 
            FROM {table}
            WHERE metadata->>'source' = %s
            ORDER BY embedding <=> %s::vector 
            LIMIT %s
        """).format(table=Identifier(self.table_name))

        params = [query_vector, source_file, query_vector, top_k]

        async with await self._get_async_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
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
