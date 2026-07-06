from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class SemanticSimilarity(BaseMetric):
    """Cosine similarity between answer and ground truth embeddings."""

    name = "semantic_similarity"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        if not ground_truth or not answer:
            return {"semantic_similarity": 0.0}
        try:
            from openai import AsyncOpenAI

            from app.core.config import settings

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            resp = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=[answer, ground_truth],
            )
            a_vec = resp.data[0].embedding
            b_vec = resp.data[1].embedding
            dot = sum(x * y for x, y in zip(a_vec, b_vec))
            norm_a = sum(x**2 for x in a_vec) ** 0.5
            norm_b = sum(x**2 for x in b_vec) ** 0.5
            sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            return {"semantic_similarity": max(0.0, sim)}
        except Exception:
            return {"semantic_similarity": 0.0}
