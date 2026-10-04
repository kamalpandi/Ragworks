from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import BaseChunkingStrategy


class RecursiveChunkingStrategy(BaseChunkingStrategy):
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str) -> list[str]:
        return self.splitter.split_text(text)
