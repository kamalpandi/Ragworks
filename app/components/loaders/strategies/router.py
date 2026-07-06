import pdfplumber.page

from app.core.config import settings
from app.observability.logger import get_logger

from .base import PageStrategy
from .table import TableStrategy
from .text import TextStrategy

logger = get_logger(__name__)


class PDFPageRouter:
    def __init__(self):
        self.text_strategy = TextStrategy()
        self.table_strategy = TableStrategy()

    def get_strategy(self, page: pdfplumber.page.Page) -> PageStrategy:
        """
        Analyzes the page content to decide the best parsing strategy.
        """

        # If table parsing is globally disabled, skip the heavy lifting
        if not settings.ENABLE_TABLE_PARSING:
            return self.text_strategy

        # 1. Broader detection settings
        # "text" strategy helps find tables even if they don't have black lines
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }

        tables = page.find_tables(table_settings)

        # 2. HEURISTIC: Calculate "Table Density"
        # We don't want to switch to table mode for a single tiny header table.

        total_page_area = page.width * page.height
        total_table_area = 0.0
        significant_tables = 0

        for table in tables:
            # table.bbox is (x0, top, x1, bottom)
            width = table.bbox[2] - table.bbox[0]
            height = table.bbox[3] - table.bbox[1]
            area = width * height

            # Filter out tiny accidental tables (e.g. page numbers, headers)
            # Check if table has enough rows to matter
            rows = table.extract()
            if not rows or len(rows) < 2:
                continue

            total_table_area += area
            significant_tables += 1

        table_coverage_ratio = total_table_area / total_page_area

        logger.debug(
            "page_table_analysis",
            page=page.page_number,
            coverage=round(table_coverage_ratio, 2),
            valid_tables=significant_tables,
        )

        # 3. Decision Logic
        # If tables cover > 15% of the page OR there are multiple significant tables
        if table_coverage_ratio > 0.15 or significant_tables >= 2:
            return self.table_strategy

        # Default fallback to simple text extraction
        return self.text_strategy
