import asyncio
import concurrent.futures

from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.core.interfaces import BaseEmbedder


class LangChainEmbeddingsWrapper(Embeddings):
    def __init__(self, embedder: BaseEmbedder):
        self.embedder = embedder

    def _run_async(self, coroutine):
        """Helper to run async code from sync context safely."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coroutine)
                return future.result()
        else:
            return asyncio.run(coroutine)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batch_size = settings.BATCH_SIZE
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            if hasattr(self.embedder, "embed_batch"):
                batch_embeddings = self._run_async(self.embedder.embed_batch(batch))
            else:
                batch_embeddings = [
                    self._run_async(self.embedder.embed_text(t)) for t in batch
                ]

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._run_async(self.embedder.embed_text(text))
