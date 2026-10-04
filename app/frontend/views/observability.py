"""Observability (log viewer) views owned by the frontend.

Plain forwarders to ``/api/v1/logs/`` (list/filter) and
``/api/v1/logs/stats``. No SSE and no state-changing routes exist, so there
is no CSRF surface here.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

logger = logging.getLogger(__name__)

router = APIRouter()

PAGE_SIZE = 50


def _filters(level, search, since, until, offset) -> dict:
    params: dict = {"limit": PAGE_SIZE, "offset": offset}
    for name, value in (
        ("level", level),
        ("search", search),
        ("since", since),
        ("until", until),
    ):
        if value:
            params[name] = value
    return params


@router.get("/ui/logs/list", response_class=HTMLResponse)
async def ui_logs_list(
    request: Request,
    level: str | None = None,
    search: str | None = None,
    since: str | None = None,
    until: str | None = None,
    offset: int = 0,
    session=Depends(require_session),
):
    resp = await get_backend_client(request).get(
        "/api/v1/logs/",
        params=_filters(level, search, since, until, offset),
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        logger.warning(
            "logs_list_failed status=%s body=%s", resp.status_code, resp.text[:200]
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/log_viewer.html",
            context={"entries": [], "error": True},
        )

    data = resp.json()
    entries = data.get("entries", [])
    total = data.get("total", 0)
    has_next = offset + PAGE_SIZE < total
    has_prev = offset > 0

    return templates.TemplateResponse(
        request=request,
        name="partials/log_viewer.html",
        context={
            "entries": entries,
            "level": level or "",
            "search": search or "",
            "since": since or "",
            "until": until or "",
            "offset": offset,
            "total": total,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_offset": offset + PAGE_SIZE if has_next else offset,
            "prev_offset": max(0, offset - PAGE_SIZE),
            "page_size": PAGE_SIZE,
            "showing_from": offset + 1 if entries else 0,
            "showing_to": offset + len(entries),
        },
    )


@router.get("/ui/logs/stats", response_class=HTMLResponse)
async def ui_logs_stats(request: Request, session=Depends(require_session)):
    resp = await get_backend_client(request).get(
        "/api/v1/logs/stats", api_key=session.api_key
    )
    if resp.status_code >= 400:
        logger.warning(
            "logs_stats_failed status=%s body=%s", resp.status_code, resp.text[:200]
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/log_stats.html",
            context={"stats": {}, "error": True},
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/log_stats.html",
        context={"stats": resp.json()},
    )
