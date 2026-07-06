from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseMetric(ABC):
    """Abstract evaluation metric for RAG quality assessment.

    Each metric computes scores for a single RAG result (query, answer, contexts, ground_truth).
    """

    name: str

    @abstractmethod
    async def compute(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        """Compute metric scores.

        Returns a dict of metric_name -> score (0.0 to 1.0).
        """
        pass
