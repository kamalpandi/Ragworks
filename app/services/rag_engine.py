import asyncio
import time
from typing import Dict, List, Optional

from app.components.llms.base import BaseLLMProvider
from app.components.query_translation import (
    QueryTranslationFactory,
    QueryTranslationStrategyType,
)
from app.components.rerankers.base import BaseReranker
from app.core.config import settings
from app.core.interfaces import BaseEmbedder, BaseVectorDB
from app.models.domain import DocumentChunk
from app.observability.logger import get_logger
from app.observability.metrics import (
    rag_active_requests,
    rag_pipeline_duration_seconds,
    rag_queries_total,
    rag_reranked_chunks,
    rag_retrieved_chunks,
    rag_step_duration_seconds,
    rag_tokens_consumed,
)
from app.observability.tracing import trace_span

logger = get_logger(__name__)


class RAGEngine:
    def __init__(
        self,
        vector_db: BaseVectorDB,
        embedder: BaseEmbedder,
        llm: BaseLLMProvider,
        system_prompt: str = "",
        reranker: BaseReranker | None = None,
    ):
        self.vector_db = vector_db
        self.embedder = embedder
        self.llm = llm
        self.system_prompt = system_prompt
        self.reranker = reranker

    async def _embed_and_search(
        self,
        query: str,
        filters: dict,
        tenant_id: str = "default",
    ) -> List[DocumentChunk]:
        vector = await self.embedder.embed_text(query)
        return await self.vector_db.search(
            vector, top_k=settings.RETRIEVAL_TOP_K, filters=filters, tenant_id=tenant_id
        )

    async def answer_question(
        self,
        query: str,
        file_filter: Optional[str] = None,
        translation_strategy: Optional[QueryTranslationStrategyType] = None,
        system_prompt: Optional[str] = None,
        tenant_id: str = "default",
        thread_id: Optional[str] = None,
    ) -> Dict:
        rag_active_requests.inc()
        pipeline_start = time.time()

        logger.info("pipeline_started", query=query[:200], thread_id=thread_id)

        # 0. Conversation Memory
        history_text = ""
        if thread_id:
            from app.services.conversation_service import get_thread

            thread = await get_thread(tenant_id, thread_id)
            if thread.messages:
                history_parts = []
                for msg in thread.messages:
                    role_label = "User" if msg.role == "user" else "Assistant"
                    history_parts.append(f"{role_label}: {msg.content}")
                history_text = "\n".join(history_parts)

        # 1. Query Translation
        queries_to_embed = [query]
        t_start = time.time()

        if translation_strategy:
            logger.info("translation_applying", strategy=translation_strategy)
            translator = QueryTranslationFactory.create(
                strategy=translation_strategy, llm=self.llm
            )
            queries_to_embed = await translator.translate(query)
            logger.info(
                "translation_complete",
                num_queries=len(queries_to_embed),
            )

        rag_step_duration_seconds.labels(step="translate").observe(
            time.time() - t_start
        )

        # 2. Construct Filter
        db_filters: dict = {}
        if file_filter:
            db_filters = {"source": {"$eq": file_filter}}

        # 3. Embed + Search ALL queries concurrently
        e_start = time.time()
        results = await asyncio.gather(
            *[
                self._embed_and_search(q, db_filters, tenant_id=tenant_id)
                for q in queries_to_embed
            ]
        )
        embed_search_duration = time.time() - e_start
        rag_step_duration_seconds.labels(step="embed_search").observe(
            embed_search_duration
        )

        # Flatten + deduplicate
        all_chunks = [chunk for batch in results for chunk in batch]
        unique_chunks = list({chunk.id: chunk for chunk in all_chunks}.values())
        rag_retrieved_chunks.observe(len(unique_chunks))
        logger.info(
            "retrieval_complete",
            unique_chunks=len(unique_chunks),
            duration_s=round(embed_search_duration, 2),
        )

        # 4. Rerank (compress to top_n most relevant)
        r_start = time.time()
        if self.reranker and len(unique_chunks) > settings.RERANK_TOP_K:
            with trace_span(
                "rag.rerank",
                {"query_len": len(query), "chunks_before": len(unique_chunks)},
            ):
                unique_chunks = await self.reranker.rerank(
                    query, unique_chunks, top_n=settings.RERANK_TOP_K
                )
                rag_reranked_chunks.observe(len(unique_chunks))
                logger.info(
                    "rerank_complete",
                    final_chunks=len(unique_chunks),
                    duration_s=round(time.time() - r_start, 2),
                )
        rag_step_duration_seconds.labels(step="rerank").observe(time.time() - r_start)

        # 5. Build context
        context_text = "\n\n".join(
            f"Source ({chunk.metadata.get('source', 'Unknown')}): {chunk.text}"
            for chunk in unique_chunks
        )

        # 6. Generate answer
        selected_prompt = system_prompt or self.system_prompt

        if history_text:
            prompt_prefix = (
                f"Previous conversation:\n{history_text}\n\n"
                f"Use the following context to answer the question.\n\n"
                f"Context:\n{context_text}\n\n"
                f"Question: {query}"
            )
        else:
            prompt_prefix = (
                f"Use the following context to answer the question.\n\n"
                f"Context:\n{context_text}\n\n"
                f"Question: {query}"
            )

        g_start = time.time()
        with trace_span("rag.generate", {"model": settings.LLM_MODEL}):
            answer = await self.llm.complete(
                prompt=prompt_prefix,
                system=selected_prompt,
            )
        gen_duration = time.time() - g_start
        rag_step_duration_seconds.labels(step="generate").observe(gen_duration)

        answer_text = answer.content if hasattr(answer, "content") else answer

        # Store conversation
        if thread_id:
            from app.services.conversation_service import store_message

            asyncio.create_task(store_message(tenant_id, thread_id, "user", query))
            asyncio.create_task(
                store_message(tenant_id, thread_id, "assistant", answer_text)
            )

        # Track token usage if available
        prompt_tokens = getattr(answer, "prompt_tokens", 0)
        completion_tokens = getattr(answer, "completion_tokens", 0)
        if prompt_tokens:
            rag_tokens_consumed.labels(type="prompt").inc(prompt_tokens)
        if completion_tokens:
            rag_tokens_consumed.labels(type="completion").inc(completion_tokens)

        # Usage tracking (fire-and-forget)
        from app.services.usage_tracker import track_query

        asyncio.create_task(
            track_query(
                tenant_id,
                prompt_tokens or 0,
                completion_tokens or 0,
                len(unique_chunks),
            )
        )

        total_duration = time.time() - pipeline_start
        rag_pipeline_duration_seconds.observe(total_duration)
        rag_active_requests.dec()
        rag_queries_total.labels(status="success").inc()

        logger.info(
            "pipeline_complete",
            total_s=round(total_duration, 2),
            chunks=len(unique_chunks),
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
        )

        return {
            "answer": answer_text,
            "citations": [c.metadata for c in unique_chunks],
            "generated_queries": queries_to_embed,
            "thread_id": thread_id,
        }
