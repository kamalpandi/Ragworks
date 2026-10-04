"""Prompt-library views owned by the frontend.

Forwarders to ``/api/v1/prompts``. Default-prompt protection is enforced by
the backend; the frontend only forwards the operation and renders the detail
(D13). "New" is a PUT upsert (no separate create endpoint).
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _detail(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, dict):
        return detail.get("message") or str(detail)
    if isinstance(detail, str) and detail:
        return detail
    return "The server could not complete the request."


async def _list(request: Request, session) -> HTMLResponse:
    resp = await get_backend_client(request).get(
        "/api/v1/prompts",
        params={"include_content": "true"},
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        logger.warning("prompts_list_failed status=%s", resp.status_code)
        return templates.TemplateResponse(
            request=request,
            name="partials/error_banner.html",
            context={"title": "Could not load prompts:", "message": _detail(resp)},
        )

    data = resp.json()
    return templates.TemplateResponse(
        request=request,
        name="partials/prompts_list.html",
        context={
            "system_prompts": data.get("system_prompts", []),
            "user_prompts": data.get("user_prompts", []),
        },
    )


@router.get("/ui/prompts/load", response_class=HTMLResponse)
async def ui_prompts_list(request: Request, session=Depends(require_session)):
    return await _list(request, session)
