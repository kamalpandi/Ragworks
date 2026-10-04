"""CSRF primitives shared by the frontend and the legacy UI layer.

Session tokens are bound to a server-side session; pre-session tokens are
short-lived and issued to unauthenticated pages (notably ``GET /login``).
"""

import hmac
import secrets
import time

from starlette.requests import Request

from app.core.config import settings


class PreSessionTokenStore:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl_seconds = ttl_seconds
        self._tokens: dict[str, float] = {}

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = time.time() + self._ttl_seconds
        return token

    def verify_and_consume(self, token: str | None) -> bool:
        if not token:
            return False
        expiry = self._tokens.pop(token, None)
        return expiry is not None and expiry > time.time()

    def cleanup(self) -> int:
        now = time.time()
        expired = [t for t, exp in self._tokens.items() if exp <= now]
        for t in expired:
            del self._tokens[t]
        return len(expired)


def tokens_match(expected: str | None, provided: str | None) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected, provided)


pre_session_tokens = PreSessionTokenStore(settings.PRE_SESSION_TTL_SECONDS)


def csrf_token_for_request(request: Request) -> str:
    """Session CSRF token when authenticated, else a fresh pre-session token."""
    session_store = getattr(request.app.state, "session_store", None)
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_store is not None and session_id:
        session = session_store.get(session_id)
        if session is not None:
            return session.csrf_token
    return pre_session_tokens.issue()


def csrf_context(request: Request) -> dict:
    """Jinja context processor: expose ``csrf_token`` to every template."""
    return {"csrf_token": csrf_token_for_request(request)}
