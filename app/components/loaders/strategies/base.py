from abc import ABC, abstractmethod

import pdfplumber.page


class PageStrategy(ABC):
    @abstractmethod
    def parse(self, page: pdfplumber.page.Page) -> str:
        """Parses a single PDF page and returns a string (Markdown/Text)"""
