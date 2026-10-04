from app.evaluation.base import BaseMetric


class ContextRecall(BaseMetric):
    """Measures what fraction of the ground truth claims are supported by retrieved contexts.

    Uses ragas if available.
    """

    name = "context_recall"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, float]:
        try:
            from ragas import SingleTurnSample
            from ragas.metrics import ContextRecall as RagasContextRecall

            from app.evaluation.metrics import _get_eval_llm

            metric = RagasContextRecall(llm=_get_eval_llm())
            sample = SingleTurnSample(
                user_input=query,
                response=answer,
                retrieved_contexts=contexts,
                reference=ground_truth or "",
            )
            score = await metric.single_turn_ascore(sample)
            return {"context_recall": float(score) if score else 0.0}
        except (ImportError, Exception):
            if not contexts or not ground_truth:
                return {"context_recall": 0.0}
            # Simple overlap: fraction of ground_truth words found in contexts
            gt_words = set(ground_truth.lower().split())
            ctx_words = set(" ".join(contexts).lower().split())
            if not gt_words:
                return {"context_recall": 0.0}
            return {"context_recall": len(gt_words & ctx_words) / len(gt_words)}
