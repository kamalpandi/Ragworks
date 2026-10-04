from pydantic import BaseModel, Field


class QueryResponse(BaseModel):
    answer: str = Field(..., description="The generated answer from the RAG engine")
    citations: list[dict] = Field(
        default_factory=list, description="List of source document metadata used"
    )
    generated_queries: list[str] = Field(
        default_factory=list, description="List of queries generated for retrieval"
    )
    thread_id: str | None = Field(
        None, description="Conversation thread ID for follow-up questions"
    )


class IngestResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion process")
    filename: str | None = Field(None, description="Name of the file ingested")
    count: int | None = Field(None, description="Number of items ingested")
    url: str | None = Field(None, description="URL ingested")
