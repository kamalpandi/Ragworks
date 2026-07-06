from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class Faithfulness(BaseMetric):
    """Measures whether the generated answer is factually grounded in the retrieved contexts.

    Uses ragas Faithfulness metric.
    """

    name = "faithfulness"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        try:
            from ragas.metrics import Faithfulness as RagasFaithfulness
            from ragas import SingleTurnSample

            metric = RagasFaithfulness()
            sample = SingleTurnSample(
                user_input=query,
                response=answer,
                retrieved_contexts=contexts,
            )
            score = await metric.single_turn_ascore(sample)
            return {"faithfulness": float(score) if score is not None else 0.0}
        except ImportError:
            if not contexts or not answer:
                return {"faithfulness": 0.0}
            # Fallback: check if answer words appear in contexts
            answer_words = set(answer.lower().split())
            ctx_words = set(" ".join(contexts).lower().split())
            if not answer_words:
                return {"faithfulness": 0.0}
            return {"faithfulness": len(answer_words & ctx_words) / len(answer_words)}
