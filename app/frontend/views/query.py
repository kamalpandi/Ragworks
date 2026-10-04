"""Query views owned by the frontend.

Reaches the backend through ``api_client`` only: chat POST and thread
history GET. Query enrichment and system-prompt resolution already live in
the API layer, so these handlers stay thin.
"""

import logging

import httpx
import markdown
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import (
    get_backend_client,
    require_session,
    verify_session_csrf,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def _chat_error(request: Request, resp: httpx.Response):
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None

    if isinstance(detail, dict):
        title = (
            "Context Window Exceeded:"
            if detail.get("error_code") == "CONTEXT_WINDOW_EXCEEDED"
            else "Internal Error:"
        )
        message = detail.get("message") or "The server could not complete the request."
    elif isinstance(detail, str) and detail:
        title, message = "Internal Error:", detail
    else:
        title, message = "Internal Error:", "The server could not complete the request."

    logger.warning("chat_failed status=%s body=%s", resp.status_code, resp.text[:200])
    return templates.TemplateResponse(
        request=request,
        name="partials/chat_error.html",
        context={"title": title, "message": message},
        headers={"HX-Retarget": "#chat-error", "HX-Reswap": "innerHTML"},
    )


@router.post("/ui/query/chat", response_class=HTMLResponse)
async def ui_query_chat(
    request: Request,
    message: str = Form(...),
    file_name: str | None = Form(None),
    translation_strategy: str | None = Form(None),
    prompt_name: str | None = Form(None),
    custom_prompt: str | None = Form(None),
    thread_id: str | None = Form(None),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)

    payload = {
        "message": message,
        "file_name": _clean(file_name),
        "translation_strategy": _clean(translation_strategy),
        "prompt_name": _clean(prompt_name),
        "custom_prompt": _clean(custom_prompt),
        "thread_id": _clean(thread_id),
    }

    resp = await get_backend_client(request).post(
        "/api/v1/query", json=payload, api_key=session.api_key
    )
    if resp.status_code >= 400:
        return _chat_error(request, resp)

    result = resp.json()
    return templates.TemplateResponse(
        request=request,
        name="partials/chat_response.html",
        context={
            "result": result,
            "html_answer": markdown.markdown(result.get("answer", "")),
            "user_question": message,
        },
    )


@router.get("/ui/query/thread/{thread_id}", response_class=HTMLResponse)
async def ui_query_thread(
    request: Request, thread_id: str, session=Depends(require_session)
):
    resp = await get_backend_client(request).get(
        f"/api/v1/conversations/{thread_id}", api_key=session.api_key
    )
    if resp.status_code >= 400:
        logger.warning(
            "thread_load_failed status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/thread_history.html",
            context={"messages": [], "unavailable": True},
        )

    messages = resp.json().get("messages", [])
    for msg in messages:
        if msg.get("role") != "user":
            msg["html"] = markdown.markdown(msg.get("content", ""))

    return templates.TemplateResponse(
        request=request,
        name="partials/thread_history.html",
        context={"messages": messages},
    )
