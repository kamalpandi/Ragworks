from functools import lru_cache

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


@lru_cache(maxsize=1)
def _get_eval_llm():
    from app.core.config import settings

    try:
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI

        if settings.LLM_PROVIDER == "deepseek" and settings.DEEPSEEK_API_KEY:
            llm = ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0,
                n=1,
            )
        else:
            llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
            )
        return LangchainLLMWrapper(llm)
    except ImportError:
        return None


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
