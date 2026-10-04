from openai import AsyncOpenAI

from app.core.config import settings
from app.core.interfaces import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    async def embed_text(self, text: str) -> list[float]:
        """Embeds a single string."""
        response = await self.client.embeddings.create(
            input=text, model=self.model, dimensions=self.dimension
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a list of strings.
        GUARANTEES it returns a List[List[float]] so .extend() works correctly.
        """

        safe_texts = [t if t.strip() else " " for t in texts]

        response = await self.client.embeddings.create(
            input=safe_texts, model=self.model, dimensions=self.dimension
        )

        return [item.embedding for item in response.data]
