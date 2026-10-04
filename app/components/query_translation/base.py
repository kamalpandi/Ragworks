from abc import ABC, abstractmethod

from app.components.llms.base import BaseLLMProvider


class BaseQueryTranslator(ABC):
    def __init__(
        self, llm: BaseLLMProvider, system_prompt: str, user_prompt_template: str
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template

    @abstractmethod
    async def translate(self, query: str) -> list[str]:
        """Translate or expand a user query into one or more optimized queries."""
