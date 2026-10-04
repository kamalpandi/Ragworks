from abc import ABC, abstractmethod
from typing import Any

from app.models.domain import DocumentChunk


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class BaseVectorDB(ABC):
    @abstractmethod
    async def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        tenant_id: str = "default",
    ):
        """Insert or update chunks and their corresponding vector embeddings."""

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> list[DocumentChunk]:
        pass

    @abstractmethod
    async def get_distinct_sources(self, tenant_id: str = "default") -> list[str]:
        """Return a list of distinct source names in the database, scoped to tenant."""


class BaseLLM(ABC):
    @abstractmethod
    async def generate_response(
        self, prompt: str, context: str, system_prompt: str | None = None
    ) -> str:
        """Generates the final answer based on prompt and context."""


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, chunks: list[DocumentChunk], top_n: int
    ) -> list[DocumentChunk]:
        """Re-rank chunks by relevance to query, returning the top_n."""


class BaseMetric(ABC):
    """Abstract evaluation metric for RAG quality assessment."""

    name: str

    @abstractmethod
    async def compute(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, float]:
        """Compute metric scores for a single RAG result."""
