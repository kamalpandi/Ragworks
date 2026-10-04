import tiktoken

from app.core.config import settings


class TokenSafeMixin:
    def __init__(
        self,
        model: str = settings.EMBEDDING_MODEL,
        max_tokens: int = settings.EMBEDDING_MODEL_MAX_TOKEN,
    ):
        self.encoder = tiktoken.encoding_for_model(model)
        self.max_tokens = max_tokens

    def enforce_token_limit(self, chunks: list[str]) -> list[str]:
        safe_chunks = []

        for chunk in chunks:
            tokens = self.encoder.encode(chunk)

            if len(tokens) <= self.max_tokens:
                safe_chunks.append(chunk)
                continue

            for i in range(0, len(tokens), self.max_tokens):
                sub_tokens = tokens[i : i + self.max_tokens]
                safe_chunks.append(self.encoder.decode(sub_tokens))

        return safe_chunks
