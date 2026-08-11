from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.models.log_entry import LogQuery
from app.observability.log_store import log_store
from app.ui import templates

router = APIRouter()

PAGE_SIZE = 50


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    return templates.TemplateResponse(request=request, name="pages/observability.html")


@router.get("/ui/logs/list", response_class=HTMLResponse)
async def htmx_logs_list(
    request: Request,
    level: str | None = None,
    search: str | None = None,
    since: str | None = None,
    until: str | None = None,
    offset: int = 0,
):
    q = LogQuery(
        level=level,
        search=search,
        since=since,
        until=until,
        limit=PAGE_SIZE,
        offset=offset,
    )
    entries = await log_store.query(q)
    total = await log_store.count(
        LogQuery(level=level, search=search, since=since, until=until)
    )

    has_next = offset + PAGE_SIZE < total
    has_prev = offset > 0
    next_offset = offset + PAGE_SIZE if has_next else offset
    prev_offset = max(0, offset - PAGE_SIZE)

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
            "next_offset": next_offset,
            "prev_offset": prev_offset,
            "page_size": PAGE_SIZE,
            "showing_from": offset + 1 if entries else 0,
            "showing_to": offset + len(entries),
        },
    )


@router.get("/ui/logs/stats", response_class=HTMLResponse)
async def htmx_logs_stats(request: Request):
    stats = await log_store.get_stats()
    return templates.TemplateResponse(
        request=request,
        name="partials/log_stats.html",
        context={"stats": stats},
    )
