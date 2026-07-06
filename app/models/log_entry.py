from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Structured log entry stored in the database."""

    id: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    level: str = "INFO"
    logger_name: str = ""
    event: str = ""
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class LogQuery(BaseModel):
    """Query parameters for log retrieval."""

    level: Optional[str] = None
    logger_name: Optional[str] = None
    event: Optional[str] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0
