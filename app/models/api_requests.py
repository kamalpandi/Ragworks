from pydantic import BaseModel, Field

from app.components.query_translation import QueryTranslationStrategyType


class IngestRequest(BaseModel):
    texts: list[str] = Field(..., description="List of text strings to ingest")


class UrlIngestRequest(BaseModel):
    url: str = Field(..., description="URL of the website to scrape and ingest")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or message")

    file_name: str | None = Field(
        None,
        description="Optional file name to filter search. Query isolation is now tenant-based.",
    )

    translation_strategy: QueryTranslationStrategyType | None = Field(
        None, description="Strategy for query translation (e.g., multi_query, hyde)"
    )
    prompt_name: str | None = Field(
        None, description="Name of the system prompt to use"
    )
    custom_prompt: str | None = Field(
        None, description="Custom system prompt text. Overrides prompt_name if set."
    )
    thread_id: str | None = Field(
        None,
        description="Conversation thread ID for follow-up questions. Created automatically if not provided.",
    )
