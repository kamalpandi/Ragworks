from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class ContextPrecision(BaseMetric):
    """Measures what fraction of retrieved contexts are relevant to the query.

    Uses ragas if available, otherwise falls back to embedding-based similarity.
    """

    name = "context_precision"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        try:
            from ragas.metrics import ContextPrecision as RagasContextPrecision
            from ragas import SingleTurnSample

            metric = RagasContextPrecision()
            sample = SingleTurnSample(
                user_input=query,
                response=answer,
                retrieved_contexts=contexts,
                reference=ground_truth or "",
            )
            score = await metric.single_turn_ascore(sample)
            return {"context_precision": float(score) if score else 0.0}
        except ImportError:
            # Fallback: simple embedding-based check
            if not contexts or not ground_truth:
                return {"context_precision": 0.0}
            # Basic overlap heuristic
            overlap = sum(
                1
                for ctx in contexts
                if any(word in ctx.lower() for word in ground_truth.lower().split())
            )
            return {"context_precision": overlap / max(len(contexts), 1)}
