from typing import Any

import pdfplumber.page

from .base import PageStrategy


class TableStrategy(PageStrategy):
    """
    Best for: Financial statements, Invoices, Data sheets.
    Logic: Detects tables, extracts text AROUND them to preserve context,
    and converts the tables to Markdown.
    """

    def _convert_table_to_markdown(self, table_data: list[list[Any]]) -> str:
        """Helper to format a list of lists into a Markdown table."""
        if not table_data:
            return ""

        # Clean data: replace None with empty string, strip whitespace
        cleaned_rows = [
            [str(cell).strip() if cell is not None else "" for cell in row]
            for row in table_data
        ]

        if not cleaned_rows:
            return ""

        markdown_lines = []

        # 1. Header row
        header = cleaned_rows[0]
        markdown_lines.append("| " + " | ".join(header) + " |")

        # 2. Separator row
        markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 3. Data rows
        for row in cleaned_rows[1:]:
            markdown_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(markdown_lines)

    def parse(self, page: pdfplumber.page.Page) -> str:
        # Settings for table detection (same as your original code)
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }

        # 1. Find and Sort Tables
        tables = page.find_tables(table_settings)
        # Sort top-to-bottom so we can read the page linearly
        tables.sort(key=lambda x: x.bbox[1])

        page_content = []
        last_bottom = 0

        # 2. Iterate through tables, extracting text in between
        for table in tables:
            _x0, top, _x1, bottom = table.bbox

            # A. Extract text occurring BEFORE this table (from last_bottom to table.top)
            if top > last_bottom:
                # crop(x0, top, x1, bottom)
                text_crop = page.crop((0, last_bottom, page.width, top))
                text = text_crop.extract_text(x_tolerance=2, y_tolerance=3)
                if text:
                    page_content.append(text)

            # B. Extract the Table itself
            # Note: We extract the data, NOT the text, to format it cleanly
            table_data = table.extract()
            if table_data:
                md_table = self._convert_table_to_markdown(table_data)
                # Adding markers helps the LLM distinguish tables from text
                page_content.append(f"\n[TABLE_START]\n{md_table}\n[TABLE_END]\n")

            last_bottom = bottom

        # 3. Extract any remaining text AFTER the last table
        if last_bottom < page.height:
            text_crop = page.crop((0, last_bottom, page.width, page.height))
            text = text_crop.extract_text(x_tolerance=2, y_tolerance=3)
            if text:
                page_content.append(text)

        return "\n\n".join(page_content)
