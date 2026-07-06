from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.domain import DocumentChunk


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class BaseVectorDB(ABC):
    @abstractmethod
    async def upsert(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        tenant_id: str = "default",
    ):
        """Insert or update chunks and their corresponding vector embeddings."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> List[DocumentChunk]:
        pass

    @abstractmethod
    async def get_distinct_sources(self, tenant_id: str = "default") -> List[str]:
        """Return a list of distinct source names in the database, scoped to tenant."""
        pass


class BaseLLM(ABC):
    @abstractmethod
    async def generate_response(
        self, prompt: str, context: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generates the final answer based on prompt and context."""
        pass


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, chunks: List[DocumentChunk], top_n: int
    ) -> List[DocumentChunk]:
        """Re-rank chunks by relevance to query, returning the top_n."""
        pass


class BaseMetric(ABC):
    """Abstract evaluation metric for RAG quality assessment."""

    name: str

    @abstractmethod
    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        """Compute metric scores for a single RAG result."""
        pass
