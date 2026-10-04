from abc import ABC, abstractmethod

from app.models.domain import DocumentChunk


class BaseReranker(ABC):
    """Pluggable cross-encoder reranker that re-scores chunks by relevance to query."""

    @abstractmethod
    async def rerank(
        self, query: str, chunks: list[DocumentChunk], top_n: int
    ) -> list[DocumentChunk]:
        """Re-rank chunks and return top_n most relevant."""
