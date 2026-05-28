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
    async def upsert(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        """Insert or update chunks and their corresponding vector embeddings."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any] | None = None,
    ) -> List[DocumentChunk]:
        pass

    @abstractmethod
    async def get_distinct_sources(self) -> List[str]:
        """Return a list of distinct source names in the database."""
        pass


class BaseLLM(ABC):
    @abstractmethod
    async def generate_response(
        self, prompt: str, context: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generates the final answer based on prompt and context."""
        pass
