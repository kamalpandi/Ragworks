from collections.abc import AsyncIterator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.components.llms.base import BaseLLMProvider, LLMResponse
from app.core.config import settings


class OllamaProvider(BaseLLMProvider):
    """
    Ollama runs locally and speaks the OpenAI protocol.
    Start: `ollama serve` then `ollama pull llama3`
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )
        self.model = settings.OLLAMA_MODEL

    @property
    def provider_name(self) -> str:
        return f"ollama/{self.model}"

    def _build_messages(
        self, prompt: str, system: str
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, system),
            temperature=settings.LLM_TEMP,
        )

        content = resp.choices[0].message.content
        if content is None:
            raise ValueError("Ollama returned an empty response.")

        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )

    # ← NOT async def (async generator = plain def returning AsyncIterator)
    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, system),
            temperature=settings.LLM_TEMP,
            stream=True,  # ← create(stream=True) not .stream() context manager
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
