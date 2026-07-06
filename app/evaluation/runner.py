from typing import Dict, List, Optional

from app.core.config import settings
from app.evaluation.base import BaseMetric
from app.evaluation.dataset import DatasetEntry
from app.evaluation.metrics import get_metric
from app.evaluation.models import EvalResult, MetricScore


class EvaluationRunner:
    """Orchestrates evaluation: load dataset -> run pipeline -> compute metrics."""

    def __init__(
        self,
        rag_engine,
        metric_names: Optional[List[str]] = None,
    ):
        self.rag_engine = rag_engine
        self.metric_names = metric_names or settings.EVAL_METRICS

    async def run(
        self,
        entries: List[DatasetEntry],
        dataset_name: str = "custom",
        file_filter: Optional[str] = None,
    ) -> EvalResult:
        """Run evaluation over a list of dataset entries."""
        metrics: List[BaseMetric] = [get_metric(name) for name in self.metric_names]
        all_scores: Dict[str, List[float]] = {m.name: [] for m in metrics}
        total = len(entries)

        for i, entry in enumerate(entries):
            result = await self.rag_engine.answer_question(
                query=entry.query,
                file_filter=file_filter,
            )
            answer = result.get("answer", "")
            contexts = [
                c.get("source_text", c.get("text", ""))
                if isinstance(c, dict)
                else getattr(c, "text", str(c))
                for c in result.get("citations", [])
            ]
            ground_truth = entry.ground_truth

            for metric in metrics:
                scores = await metric.compute(
                    query=entry.query,
                    answer=answer,
                    contexts=contexts,
                    ground_truth=ground_truth,
                )
                for key, value in scores.items():
                    if key not in all_scores:
                        all_scores[key] = []
                    all_scores[key].append(value)

        # Aggregate
        metric_scores = []
        aggregated = {}
        for name, values in all_scores.items():
            if values:
                avg = sum(values) / len(values)
                aggregated[name] = avg
                metric_scores.append(
                    MetricScore(
                        name=name,
                        value=avg,
                        description=f"Mean over {len(values)} samples",
                    )
                )

        result = EvalResult(
            dataset_name=dataset_name,
            num_samples=total,
            metrics=metric_scores,
            aggregated_scores=aggregated,
            config_snapshot={
                "reranker_enabled": settings.RERANKER_ENABLED,
                "reranker_provider": settings.RERANKER_PROVIDER,
                "chunking_strategy": settings.CHUNKING_STRATEGY,
                "top_k": settings.TOP_K,
                "llm_model": settings.LLM_MODEL,
            },
        )
        result.store(settings.EVAL_RESULTS_DIR)
        return result
