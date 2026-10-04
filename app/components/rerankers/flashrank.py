from app.components.rerankers.base import BaseReranker
from app.core.config import settings
from app.models.domain import DocumentChunk


class FlashRankReranker(BaseReranker):
    """Cross-encoder reranker using FlashRank (ONNX-based, fast on CPU)."""

    def __init__(self):
        self._model = None
        self._model_name = settings.FLASHRANK_MODEL

    def _lazy_load(self):
        if self._model is not None:
            return
        from flashrank import Ranker

        self._model = Ranker(model_name=self._model_name)

    async def rerank(
        self, query: str, chunks: list[DocumentChunk], top_n: int
    ) -> list[DocumentChunk]:
        if not chunks:
            return []
        if len(chunks) <= top_n:
            return chunks

        self._lazy_load()
        from flashrank.Ranker import RerankRequest

        passages = [
            {"text": chunk.text, "meta": {"idx": i}} for i, chunk in enumerate(chunks)
        ]
        request = RerankRequest(query=query, passages=passages)
        results = self._model.rerank(request)

        top_indices = [r["meta"]["idx"] for r in results[:top_n]]
        return [chunks[i] for i in top_indices]
