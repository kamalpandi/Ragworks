"""Server-side session storage for the render-only frontend.

A session holds the backend API key server-side. The browser only ever
receives an opaque session identifier in an HttpOnly cookie.
"""

import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Session:
    session_id: str
    api_key: str
    tenant_id: str
    csrf_token: str
    created_at: float
    expires_at: float


class SessionStore(ABC):
    """Interface for session storage (in-memory today, Postgres later)."""

    @abstractmethod
    def create(
        self, api_key: str, tenant_id: str, ttl_seconds: int | None = None
    ) -> Session: ...

    @abstractmethod
    def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    def delete(self, session_id: str) -> None: ...

    @abstractmethod
    def cleanup(self) -> int: ...


class InMemorySessionStore(SessionStore):
    def __init__(self, ttl_seconds: int = 28800):
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}

    def create(
        self, api_key: str, tenant_id: str, ttl_seconds: int | None = None
    ) -> Session:
        ttl = self._ttl_seconds if ttl_seconds is None else ttl_seconds
        now = time.time()
        session = Session(
            session_id=secrets.token_urlsafe(32),
            api_key=api_key,
            tenant_id=tenant_id,
            csrf_token=secrets.token_urlsafe(32),
            created_at=now,
            expires_at=now + ttl,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.expires_at <= time.time():
            del self._sessions[session_id]
            return None
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cleanup(self) -> int:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if s.expires_at <= now]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
