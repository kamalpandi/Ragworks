from datetime import datetime

from pydantic import BaseModel


class ConversationMessage(BaseModel):
    id: str | None = None
    tenant_id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime | None = None


class ConversationThread(BaseModel):
    thread_id: str
    tenant_id: str
    messages: list[ConversationMessage] = []
