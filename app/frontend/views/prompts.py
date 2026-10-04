"""Prompt-library views owned by the frontend.

Forwarders to ``/api/v1/prompts``. Default-prompt protection is enforced by
the backend; the frontend only forwards the operation and renders the detail
(D13). "New" is a PUT upsert (no separate create endpoint).
"""

import logging

import httpx
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


def _error(request: Request, message: str, *, retarget: bool):
    headers = (
        {"HX-Retarget": "#prompts-error", "HX-Reswap": "innerHTML"}
        if retarget
        else None
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/error_banner.html",
        context={"title": "Prompt error:", "message": message},
        headers=headers,
    )


@router.get("/ui/prompts/load", response_class=HTMLResponse)
async def ui_prompts_list(request: Request, session=Depends(require_session)):
    return await _list(request, session)


@router.get("/ui/prompts/new", response_class=HTMLResponse)
async def ui_prompts_new(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(
        request=request,
        name="partials/prompt_edit.html",
        context={
            "name": "",
            "category": "system",
            "content": "",
            "is_new": True,
        },
    )


@router.get("/ui/prompts/edit/{category}/{name}", response_class=HTMLResponse)
async def ui_prompts_edit(
    request: Request,
    category: str,
    name: str,
    session=Depends(require_session),
):
    resp = await get_backend_client(request).get(
        f"/api/v1/prompts/{name}",
        params={"category": category},
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        logger.warning("prompts_edit_failed status=%s name=%s", resp.status_code, name)
        return _error(request, _detail(resp), retarget=True)

    data = resp.json()
    return templates.TemplateResponse(
        request=request,
        name="partials/prompt_edit.html",
        context={
            "name": data.get("name", name),
            "category": data.get("category", category),
            "content": data.get("content", ""),
            "is_new": False,
        },
    )


@router.post("/ui/prompts/save", response_class=HTMLResponse)
async def ui_prompts_save(
    request: Request,
    name: str = Form(""),
    content: str = Form(""),
    category: str = Form("system"),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)

    name = name.strip()
    category = category.strip()
    if not name:
        return _error(request, "Prompt name is required", retarget=True)

    resp = await get_backend_client(request).put(
        f"/api/v1/prompts/{name}",
        json={"category": category, "content": content},
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        logger.warning("prompts_save_failed status=%s name=%s", resp.status_code, name)
        return _error(request, _detail(resp), retarget=True)

    return await _list(request, session)


@router.delete("/ui/prompts/delete/{category}/{name}", response_class=HTMLResponse)
async def ui_prompts_delete(
    request: Request,
    category: str,
    name: str,
    session=Depends(require_session),
):
    verify_session_csrf(request, session)
    resp = await get_backend_client(request).delete(
        f"/api/v1/prompts/{name}",
        params={"category": category},
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        logger.warning(
            "prompts_delete_failed status=%s name=%s", resp.status_code, name
        )
        return _error(request, _detail(resp), retarget=True)

    return await _list(request, session)
