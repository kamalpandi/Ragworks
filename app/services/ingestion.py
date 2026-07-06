import asyncio
import time
import uuid
from typing import List

from app.components.chunking.factory import ChunkingFactory
from app.components.embedders.langchain_wrapper import LangChainEmbeddingsWrapper
from app.core.config import settings
from app.core.interfaces import BaseEmbedder, BaseVectorDB
from app.models.domain import DocumentChunk
from app.observability.logger import get_logger

logger = get_logger(__name__)


class IngestionService:
    def __init__(self, embedder: BaseEmbedder, vector_db: BaseVectorDB):
        self.embedder = embedder
        self.vector_db = vector_db

    async def ingest_texts(
        self, texts: List[str], source_name: str, tenant_id: str = "default"
    ):
        start_time = time.time()
        logger.info("ingest_started", source=source_name, num_texts=len(texts))

        # 1. Chunking
        logger.info("chunking_applying", strategy=settings.CHUNKING_STRATEGY)

        lc_embedder = LangChainEmbeddingsWrapper(self.embedder)
        chunker = ChunkingFactory.create(
            strategy=settings.CHUNKING_STRATEGY, embedder=lc_embedder, token_safe=True
        )

        all_chunks: List[DocumentChunk] = []
        total_tokens = 0

        for text in texts:
            raw_chunks = chunker.chunk(text)
            logger.info("chunk_block", chunks=len(raw_chunks))

            for i, chunk_text in enumerate(raw_chunks):
                chunk_id = f"{source_name}-chunk-{i}-{str(uuid.uuid4())[:8]}"

                doc_chunk = DocumentChunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata={
                        "source": source_name,
                        "chunk_index": i,
                        "strategy": settings.CHUNKING_STRATEGY,
                        "tenant_id": tenant_id,
                    },
                )
                all_chunks.append(doc_chunk)
                total_tokens += len(chunk_text.split())

        if not all_chunks:
            logger.error("ingest_no_chunks")
            return

        logger.info("chunking_complete", total_chunks=len(all_chunks))

        # 2. Embedding
        logger.info("embedding_started", batch_size=settings.BATCH_SIZE)
        vectors = []

        total = len(all_chunks)
        for i in range(0, total, settings.BATCH_SIZE):
            batch = all_chunks[i : i + settings.BATCH_SIZE]
            batch_texts = [c.text for c in batch]

            batch_vectors = await self.embedder.embed_batch(batch_texts)
            vectors.extend(batch_vectors)

            logger.info(
                "embedding_progress",
                embedded=min(i + settings.BATCH_SIZE, total),
                total=total,
            )

        logger.info(
            "embedding_complete",
            chunks=len(all_chunks),
            vectors=len(vectors),
        )

        # 3. Storage
        logger.info("upserting_to_vector_db")
        await self.vector_db.upsert(all_chunks, vectors, tenant_id=tenant_id)

        # Usage tracking (fire-and-forget)
        from app.services.usage_tracker import track_ingest

        asyncio.create_task(track_ingest(tenant_id, len(all_chunks), source_name))

        duration = time.time() - start_time
        logger.info("ingest_complete", duration_s=round(duration, 2))
