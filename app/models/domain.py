from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    id: str
    text: str
    vector: list[float] | None = None
    metadata: dict = Field(default_factory=dict)
    score: float | None = None
