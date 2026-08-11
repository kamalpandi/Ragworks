from typing import AsyncIterator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.components.llms.base import BaseLLMProvider, LLMResponse
from app.core.config import settings


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = settings.DEEPSEEK_MODEL

    @property
    def provider_name(self) -> str:
        return f"deepseek/{self.model}"

    def _build_messages(
        self, prompt: str, system: str
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, system),
            temperature=settings.LLM_TEMP,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("DeepSeek returned an empty response.")

        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
        )

    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, system),
            temperature=settings.LLM_TEMP,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
