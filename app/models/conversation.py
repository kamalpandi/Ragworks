from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ConversationMessage(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    thread_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None


class ConversationThread(BaseModel):
    thread_id: str
    tenant_id: str
    messages: List[ConversationMessage] = []
