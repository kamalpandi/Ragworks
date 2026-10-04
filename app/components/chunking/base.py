from abc import ABC, abstractmethod


class BaseChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, text: str) -> list[str]:
        pass
