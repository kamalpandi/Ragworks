from app.evaluation.metrics.retrieval.context_precision import ContextPrecision
from app.evaluation.metrics.retrieval.context_recall import ContextRecall
from app.evaluation.metrics.retrieval.hit_rate import HitRate
from app.evaluation.metrics.retrieval.mrr import MRR
from app.evaluation.metrics.generation.faithfulness import Faithfulness
from app.evaluation.metrics.generation.answer_relevancy import AnswerRelevancy
from app.evaluation.metrics.generation.correctness import Correctness
from app.evaluation.metrics.endtoend.semantic_similarity import SemanticSimilarity
from app.evaluation.metrics.endtoend.bleu_rouge import BleuRouge

_metric_registry: dict = {}


def _register(cls):
    _metric_registry[cls.name] = cls
    return cls


def get_metric(name: str):
    """Resolve a metric by name, with lazy auto-import for ragas metrics."""
    if name not in _metric_registry:
        # Try ragas-backed metrics
        if name == "faithfulness":
            _register(Faithfulness)
        elif name == "answer_relevancy":
            _register(AnswerRelevancy)
        elif name == "correctness":
            _register(Correctness)
        elif name == "context_precision":
            _register(ContextPrecision)
        elif name == "context_recall":
            _register(ContextRecall)
        elif name == "hit_rate":
            _register(HitRate)
        elif name == "mrr":
            _register(MRR)
        elif name == "semantic_similarity":
            _register(SemanticSimilarity)
        elif name == "bleu_rouge":
            _register(BleuRouge)
        else:
            raise ValueError(f"Unknown metric: '{name}'")

    metric_cls = _metric_registry[name]
    return metric_cls()


def list_available_metrics() -> list[str]:
    return sorted(_metric_registry.keys())


__all__ = [
    "get_metric",
    "list_available_metrics",
    "ContextPrecision",
    "ContextRecall",
    "HitRate",
    "MRR",
    "Faithfulness",
    "AnswerRelevancy",
    "Correctness",
    "SemanticSimilarity",
    "BleuRouge",
]
