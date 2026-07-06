from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class Correctness(BaseMetric):
    """Measures factual correctness of the answer against ground truth.

    Uses ragas Correctness metric (requires ground_truth).
    """

    name = "correctness"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        if not ground_truth:
            return {"correctness": 0.0}
        try:
            from ragas.metrics import Correctness as RagasCorrectness
            from ragas import SingleTurnSample

            metric = RagasCorrectness()
            sample = SingleTurnSample(
                user_input=query,
                response=answer,
                retrieved_contexts=contexts,
                reference=ground_truth,
            )
            score = await metric.single_turn_ascore(sample)
            return {"correctness": float(score) if score is not None else 0.0}
        except ImportError:
            # Fallback: simple string overlap with ground truth
            gt_words = set(ground_truth.lower().split())
            answer_words = set(answer.lower().split())
            if not gt_words:
                return {"correctness": 0.0}
            return {"correctness": len(gt_words & answer_words) / len(gt_words)}
