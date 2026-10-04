from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Structured log entry stored in the database."""

    id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    level: str = "INFO"
    logger_name: str = ""
    event: str = ""
    trace_id: str | None = None
    request_id: str | None = None
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class LogQuery(BaseModel):
    """Query parameters for log retrieval."""

    level: str | None = None
    logger_name: str | None = None
    event: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    since: str | None = None
    until: str | None = None
    search: str | None = None
    limit: int = 100
    offset: int = 0
