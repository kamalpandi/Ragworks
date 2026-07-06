from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class AnswerRelevancy(BaseMetric):
    """Measures how relevant the generated answer is to the original query.

    Uses ragas AnswerRelevancy metric.
    """

    name = "answer_relevancy"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        try:
            from ragas.metrics import AnswerRelevancy as RagasAnswerRelevancy
            from ragas import SingleTurnSample

            metric = RagasAnswerRelevancy()
            sample = SingleTurnSample(
                user_input=query,
                response=answer,
                retrieved_contexts=contexts,
            )
            score = await metric.single_turn_ascore(sample)
            return {"answer_relevancy": float(score) if score is not None else 0.0}
        except ImportError:
            if not answer:
                return {"answer_relevancy": 0.0}
            # Fallback: word overlap between query and answer
            query_words = set(query.lower().split())
            answer_words = set(answer.lower().split())
            if not query_words:
                return {"answer_relevancy": 0.0}
            return {
                "answer_relevancy": len(query_words & answer_words) / len(query_words)
            }
