from typing import List, Optional

from pydantic import BaseModel, Field


class QueryResponse(BaseModel):
    answer: str = Field(..., description="The generated answer from the RAG engine")
    citations: List[dict] = Field(
        default_factory=list, description="List of source document metadata used"
    )
    generated_queries: List[str] = Field(
        default_factory=list, description="List of queries generated for retrieval"
    )
    thread_id: Optional[str] = Field(
        None, description="Conversation thread ID for follow-up questions"
    )


class IngestResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion process")
    filename: Optional[str] = Field(None, description="Name of the file ingested")
    count: Optional[int] = Field(None, description="Number of items ingested")
    url: Optional[str] = Field(None, description="URL ingested")
