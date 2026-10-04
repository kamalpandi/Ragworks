from app.evaluation.base import BaseMetric


class MRR(BaseMetric):
    """Mean Reciprocal Rank: 1 / rank of the first relevant chunk.

    Relevance is determined by whether ground_truth string appears in the chunk.
    """

    name = "mrr"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, float]:
        if not contexts or not ground_truth:
            return {"mrr": 0.0}
        for i, ctx in enumerate(contexts):
            if ground_truth.lower() in ctx.lower():
                return {"mrr": 1.0 / (i + 1)}
        return {"mrr": 0.0}
