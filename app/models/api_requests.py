from typing import List, Optional

from pydantic import BaseModel, Field

from app.components.query_translation import QueryTranslationStrategyType


class IngestRequest(BaseModel):
    texts: List[str] = Field(..., description="List of text strings to ingest")


class UrlIngestRequest(BaseModel):
    url: str = Field(..., description="URL of the website to scrape and ingest")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or message")

    file_name: Optional[str] = Field(
        None,
        description="Optional file name to filter search. Query isolation is now tenant-based.",
    )

    translation_strategy: Optional[QueryTranslationStrategyType] = Field(
        None, description="Strategy for query translation (e.g., multi_query, hyde)"
    )
    prompt_name: Optional[str] = Field(
        None, description="Name of the system prompt to use"
    )
    custom_prompt: Optional[str] = Field(
        None, description="Custom system prompt text. Overrides prompt_name if set."
    )
    thread_id: Optional[str] = Field(
        None,
        description="Conversation thread ID for follow-up questions. Created automatically if not provided.",
    )
