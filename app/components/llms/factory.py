from functools import lru_cache

from app.components.llms.base import BaseLLMProvider
from app.core.config import settings


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseLLMProvider:
    """
    Returns the correct LLM backend based on LLM_PROVIDER env var.
    Cached so the model is only loaded once per process.
    """
    match settings.LLM_PROVIDER:
        case "openai":
            from app.components.llms.openai_llm import OpenAIProvider

            return OpenAIProvider()

        case "deepseek":
            from app.components.llms.deepseek_llm import DeepSeekProvider

            return DeepSeekProvider()

        case "ollama":
            from app.components.llms.ollama_llm import OllamaProvider

            return OllamaProvider()

        case "llamacpp":
            from app.components.llms.llamacpp_llm import LlamaCppProvider

            return LlamaCppProvider()

        case _:
            raise ValueError(f"Unknown LLM_PROVIDER: '{settings.LLM_PROVIDER}'")
