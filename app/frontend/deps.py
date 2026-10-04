"""FastAPI dependencies for frontend views."""

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.csrf import csrf_token_for_request
from app.core.sessions import InMemorySessionStore, Session
from app.frontend.api_client import BackendClient
from app.frontend.csrf import pre_session_tokens, tokens_match


def get_session_store(request: Request) -> InMemorySessionStore:
    return request.app.state.session_store


def get_backend_client(request: Request) -> BackendClient:
    return request.app.state.backend_client


def get_session(request: Request) -> Session | None:
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return get_session_store(request).get(session_id)


def require_session(request: Request) -> Session:
    session = get_session(request)
    if session is None:
        if request.headers.get("HX-Request"):
            # HTMX would otherwise follow the 302 and swap the login page into
            # the target element. HX-Redirect triggers a full-page navigation.
            raise HTTPException(
                status_code=status.HTTP_200_OK, headers={"HX-Redirect": "/login"}
            )
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": f"/login?next={request.url.path}"},
        )
    return session


def get_csrf_token(request: Request) -> str:
    """Return the session CSRF token, or a pre-session token if unauthenticated."""
    return csrf_token_for_request(request)


def verify_session_csrf(request: Request, session: Session) -> None:
    if not tokens_match(
        session.csrf_token, request.headers.get(settings.CSRF_HEADER_NAME)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )


def verify_pre_session_csrf(request: Request) -> bool:
    return pre_session_tokens.verify_and_consume(
        request.headers.get(settings.CSRF_HEADER_NAME)
    )
