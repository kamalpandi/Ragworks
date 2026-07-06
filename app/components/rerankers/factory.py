from functools import lru_cache

from app.components.rerankers.base import BaseReranker
from app.core.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> BaseReranker | None:
    """Returns the configured reranker, or None if reranking is disabled."""
    if not settings.RERANKER_ENABLED:
        return None

    match settings.RERANKER_PROVIDER:
        case "flashrank":
            from app.components.rerankers.flashrank import FlashRankReranker

            return FlashRankReranker()
        case "bge":
            raise NotImplementedError(
                "BGE reranker not yet implemented. "
                "Set RERANKER_PROVIDER=flashrank or contribute a BGE implementation."
            )
        case "cohere":
            raise NotImplementedError(
                "Cohere reranker not yet implemented. "
                "Set RERANKER_PROVIDER=flashrank or contribute a Cohere implementation."
            )
        case _:
            raise ValueError(
                f"Unknown RERANKER_PROVIDER: '{settings.RERANKER_PROVIDER}'"
            )


class RerankerFactory:
    """Factory for creating reranker instances (non-cached variant)."""

    @staticmethod
    def create(
        provider: str = settings.RERANKER_PROVIDER,
    ) -> BaseReranker | None:
        return get_reranker()
