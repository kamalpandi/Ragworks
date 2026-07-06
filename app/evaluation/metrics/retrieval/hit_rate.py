from typing import Dict, List, Optional

from app.evaluation.base import BaseMetric


class HitRate(BaseMetric):
    """Simple retrieval metric: did any chunk contain the ground truth answer string?"""

    name = "hit_rate"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        if not contexts or not ground_truth:
            return {"hit_rate": 0.0}
        hit = any(ground_truth.lower() in ctx.lower() for ctx in contexts)
        return {"hit_rate": 1.0 if hit else 0.0}
