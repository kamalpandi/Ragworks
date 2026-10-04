from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> LLMResponse: ...

    @abstractmethod
    def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        # returning an AsyncIterator
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    async def generate_response(self, prompt: str, system: str = "") -> LLMResponse:
        """
        An alias mapping to complete() to satisfy external structural calls
        without breaking downstream components.
        """
        return await self.complete(prompt=prompt, system=system)
