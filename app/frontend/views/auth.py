"""Frontend authentication views.

Login validates the submitted API key against the backend identity endpoint,
then stores the key in a server-side session. The browser only receives an
opaque, HttpOnly session cookie.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.frontend import templates
from app.frontend.csrf import pre_session_tokens, tokens_match
from app.frontend.deps import (
    get_backend_client,
    get_csrf_token,
    get_session,
    get_session_store,
)

router = APIRouter()


def _safe_next(next_path: str | None) -> str:
    if not next_path or not next_path.startswith("/") or next_path.startswith("//"):
        return "/"
    return next_path


def _render_login(
    request: Request, next_path: str, error: str | None, status_code: int
):
    return templates.TemplateResponse(
        request=request,
        name="pages/login.html",
        context={
            "csrf_token": get_csrf_token(request),
            "next": next_path,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    return _render_login(request, _safe_next(next), None, 200)


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    token = request.headers.get(settings.CSRF_HEADER_NAME) or str(
        form.get("csrf_token", "")
    )
    next_path = _safe_next(str(form.get("next", "/")))

    if not pre_session_tokens.verify_and_consume(token):
        return _render_login(
            request, next_path, "Invalid or expired form. Please try again.", 403
        )

    api_key = str(form.get("api_key", "")).strip()
    if not api_key:
        return _render_login(request, next_path, "API key is required", 400)

    response = await get_backend_client(request).get("/api/v1/auth/me", api_key=api_key)
    if response.status_code != 200:
        return _render_login(request, next_path, "Invalid API key", 401)

    tenant_id = response.json().get("tenant_id", "default")
    session = get_session_store(request).create(api_key, tenant_id)

    redirect = RedirectResponse(url=next_path, status_code=303)
    redirect.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session.session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )
    return redirect


@router.post("/logout")
async def logout(request: Request):
    session = get_session(request)
    if session is not None:
        form = await request.form()
        token = request.headers.get(settings.CSRF_HEADER_NAME) or str(
            form.get("csrf_token", "")
        )
        if not tokens_match(session.csrf_token, token):
            return HTMLResponse("Invalid CSRF token", status_code=403)
        get_session_store(request).delete(session.session_id)

    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return redirect
