import time
from typing import Any, Dict, List, Optional, cast

from pinecone import ServerlessSpec, Vector
from pinecone.grpc import PineconeGRPC as Pinecone

from app.core.config import settings
from app.core.interfaces import BaseVectorDB
from app.models.domain import DocumentChunk
from app.observability.logger import get_logger

logger = get_logger(__name__)


class PineconeDB(BaseVectorDB):
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self._initialize_index()
        self.index = self.pc.Index(self.index_name)

    def _initialize_index(self):
        existing_indexes = [i.name for i in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            spec = ServerlessSpec(cloud=settings.CLOUD, region=settings.REGION)

            self.pc.create_index(
                name=self.index_name,
                dimension=settings.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=spec,
            )

            while True:
                description = self.pc.describe_index(self.index_name)

                if (
                    description is not None
                    and description.status is not None
                    and description.status.ready is True
                ):
                    break
                time.sleep(1)

    async def upsert(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        tenant_id: str = "default",
    ):
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match!")

        vectors: List[Vector] = []

        for chunk, embedding in zip(chunks, embeddings):
            meta: dict[str, float | int | list[float] | list[int] | list[str] | str] = (
                chunk.metadata.copy() if chunk.metadata else {}
            )
            meta["text"] = chunk.text

            vectors.append(
                Vector(
                    id=chunk.id,
                    values=embedding,
                    metadata=meta,
                )
            )

        self.index.upsert(vectors=vectors, namespace=tenant_id)

    async def get_distinct_sources(self, tenant_id: str = "default") -> List[str]:
        return []

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
    ) -> List[DocumentChunk]:
        if len(query_vector) != settings.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Query vector size {len(query_vector)} does not match Index dimension {settings.EMBEDDING_DIMENSION}"
            )

        # 1. Execute the query
        raw_res = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filters,
            namespace=tenant_id,
        )

        res = cast(Any, raw_res)

        results = []
        for match in res.matches:
            metadata = match.metadata if match.metadata is not None else {}
            text_content = str(metadata.get("text", ""))

            results.append(
                DocumentChunk(
                    id=str(match.id),
                    text=text_content,
                    metadata=dict(metadata),
                    score=float(match.score) if match.score is not None else 0.0,
                )
            )
        return results
